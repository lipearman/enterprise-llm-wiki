"""
Re-embed all content in Supabase using the current OLLAMA_EMBED_MODEL.

Run AFTER applying sql/006_bge_m3_migration.sql in Supabase SQL Editor:

    cd backend
    python scripts/reembed_all.py

Progress is logged to stdout. The script is idempotent — rows that already
have a non-null embedding are skipped unless --force is passed.
"""

import asyncio
import sys
import time
import argparse

# ── path setup ────────────────────────────────────────────────────────────────
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# ──────────────────────────────────────────────────────────────────────────────

from app.db.supabase_client import supabase
from app.services.ollama_client import embed_llm
from app.core.config import settings
from app.core.text import normalize_question


BATCH = 20        # rows per Supabase upsert batch
SLEEP = 0.05      # seconds between embedding calls (rate-limit safety)
# mxbai-embed-large on this server crashes above ~1020 ASCII chars.
# 1500 chars is used here; content is mostly Thai so effective token count
# stays well within the 512-token window.
MAX_CHARS = 1500


async def embed_text(text: str) -> list[float]:
    """Embed text, truncating to MAX_CHARS to avoid model OOM on long inputs."""
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS]
    return await embed_llm.embed(text)


async def reembed_wiki_pages(force: bool) -> None:
    print("\n=== wiki_pages ===")
    query = supabase.table("wiki_pages").select("id,title,content_markdown,embedding")
    if not force:
        query = query.is_("embedding", "null")
    rows = query.execute().data or []
    print(f"  Rows to embed: {len(rows)}")
    ok = err = 0
    for row in rows:
        try:
            emb = await embed_text(row.get("content_markdown") or row.get("title") or "")
            supabase.table("wiki_pages").update({"embedding": emb}).eq("id", row["id"]).execute()
            ok += 1
            if ok % 10 == 0:
                print(f"  ... {ok}/{len(rows)}")
            await asyncio.sleep(SLEEP)
        except Exception as e:
            print(f"  [ERR] id={row['id']} title={row.get('title','')[:40]}: {e}")
            err += 1
    print(f"  Done: {ok} ok, {err} errors")


async def reembed_document_chunks(force: bool) -> None:
    print("\n=== document_chunks ===")
    query = supabase.table("document_chunks").select("id,content,embedding")
    if not force:
        query = query.is_("embedding", "null")
    rows = query.execute().data or []
    print(f"  Rows to embed: {len(rows)}")
    ok = err = 0
    for row in rows:
        try:
            emb = await embed_text(row.get("content") or "")
            supabase.table("document_chunks").update({"embedding": emb}).eq("id", row["id"]).execute()
            ok += 1
            if ok % 50 == 0:
                print(f"  ... {ok}/{len(rows)}")
            await asyncio.sleep(SLEEP)
        except Exception as e:
            print(f"  [ERR] id={row['id']}: {e}")
            err += 1
    print(f"  Done: {ok} ok, {err} errors")


async def reembed_canonical_qa(force: bool) -> None:
    print("\n=== canonical_qa ===")
    query = supabase.table("canonical_qa").select("id,question,embedding")
    if not force:
        query = query.is_("embedding", "null")
    rows = query.execute().data or []
    print(f"  Rows to embed: {len(rows)}")
    ok = err = 0
    for row in rows:
        try:
            emb = await embed_text(normalize_question(row.get("question") or ""))
            supabase.table("canonical_qa").update({"embedding": emb}).eq("id", row["id"]).execute()
            ok += 1
            if ok % 50 == 0:
                print(f"  ... {ok}/{len(rows)}")
            await asyncio.sleep(SLEEP)
        except Exception as e:
            print(f"  [ERR] id={row['id']}: {e}")
            err += 1
    print(f"  Done: {ok} ok, {err} errors")


async def clear_answer_cache() -> None:
    """Answer cache is cheap to rebuild — just clear it."""
    print("\n=== answer_cache (clearing) ===")
    supabase.table("answer_cache").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    print("  Cleared.")


async def main(force: bool) -> None:
    t0 = time.time()
    print(f"Re-embedding with model: {settings.OLLAMA_EMBED_MODEL}  dim={settings.EMBEDDING_DIM}")
    print(f"Embed server: {settings.OLLAMA_EMBED_BASE_URL}")

    # Quick smoke test
    test_emb = await embed_llm.embed("test")
    if len(test_emb) != settings.EMBEDDING_DIM:
        print(f"\n[FATAL] Model returned {len(test_emb)}-dim vector but EMBEDDING_DIM={settings.EMBEDDING_DIM}")
        print("        Update EMBEDDING_DIM in .env and retry.")
        sys.exit(1)
    print(f"Smoke test OK: dim={len(test_emb)}")

    await reembed_wiki_pages(force)
    await reembed_document_chunks(force)
    await reembed_canonical_qa(force)
    await clear_answer_cache()

    elapsed = time.time() - t0
    print(f"\nFinished in {elapsed:.1f}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Re-embed all content with current embed model")
    parser.add_argument("--force", action="store_true",
                        help="Re-embed ALL rows, not just those with NULL embedding")
    args = parser.parse_args()
    asyncio.run(main(args.force))
