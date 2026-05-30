#!/usr/bin/env python
"""
Re-embed all document_chunks, wiki_pages, and canonical_qa with a new model.

Usage:
    cd backend
    python -m eval.migrate_embeddings --model bge-m3 --company DEVES
    python -m eval.migrate_embeddings --model bge-m3          # all companies
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.db.supabase_client import supabase
from app.services.ollama_client import OllamaClient
from app.core.config import settings


async def re_embed_table(
    client: OllamaClient,
    model: str,
    table: str,
    content_col: str,
    company_code: str | None,
    batch_size: int = 10,
) -> tuple[int, int]:
    print(f"\n── {table}.{content_col} ──────────────────")

    q = supabase.table(table).select(f"id,{content_col}")
    if company_code:
        q = q.eq("company_code", company_code)
    rows  = (q.execute().data or [])
    total = len(rows)
    print(f"  {total} rows")
    if total == 0:
        return 0, 0

    ok = fail = 0
    for i in range(0, total, batch_size):
        for row in rows[i : i + batch_size]:
            text = (row.get(content_col) or "").strip()
            if not text:
                continue
            try:
                emb = await client.embed(text[:8000], model=model)
                supabase.table(table).update({"embedding": emb}).eq("id", row["id"]).execute()
                ok += 1
            except Exception as exc:
                fail += 1
                print(f"\n  ✗ {row['id'][:8]}… {exc}")
        done = min(i + batch_size, total)
        print(f"  {done}/{total} ({done/total*100:.0f}%)  ok={ok} fail={fail}", end="\r", flush=True)
        await asyncio.sleep(0.05)

    print(f"\n  ✓ ok={ok}  fail={fail}")
    return ok, fail


async def main(model: str, company_code: str | None, base_url: str = "http://localhost:11434") -> None:
    client = OllamaClient(base_url)

    print(f"Model   : {model}")
    print(f"Base URL: {base_url}")
    print(f"Company : {company_code or 'ALL'}\n")

    # Sanity check
    try:
        dim = len(await client.embed("test", model=model))
        print(f"✓ model ok — dim={dim}")
    except Exception as e:
        print(f"✗ model not available: {e}")
        sys.exit(1)

    t0 = time.time()
    for table, col in [
        ("document_chunks", "content"),
        ("wiki_pages",      "content_markdown"),
        ("canonical_qa",    "question"),
    ]:
        await re_embed_table(client, model, table, col, company_code)

    print(f"\nDone in {time.time()-t0:.0f}s")
    print("\nNext: deploy backend with OLLAMA_EMBED_MODEL=bge-m3 in .env")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model",    default="bge-m3")
    parser.add_argument("--company",  default=None)
    parser.add_argument("--base-url", default="http://localhost:11434",
                        help="Ollama embed base URL (default: http://localhost:11434)")
    args = parser.parse_args()
    asyncio.run(main(args.model, args.company, args.base_url))
