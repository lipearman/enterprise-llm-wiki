"""Debug script: show actual retrieval scores for the shareholders question."""
import sys, io, asyncio, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.ollama_client import embed_llm
from app.core.text import normalize_question
from app.db.supabase_client import supabase


async def main():
    question = "ผู้ถือหุ้นรายใหญ่ของเทเวศประกันภัยคือใคร"
    q_emb = await embed_llm.embed(normalize_question(question))

    # Top 20 document_chunks
    res = supabase.rpc("match_document_chunks", {
        "query_embedding": q_emb,
        "match_company_code": "DEVES",
        "match_threshold": 0.3,
        "match_count": 20,
    }).execute()
    print("=== document_chunks (top 20) ===")
    for r in (res.data or []):
        content_preview = (r.get("content") or "")[:120].replace("\n", " ")
        print(f"  score={r['similarity']:.4f} | {content_preview}")

    print()

    # Top 10 wiki_pages
    res2 = supabase.rpc("match_wiki_pages", {
        "query_embedding": q_emb,
        "match_company_code": "DEVES",
        "match_threshold": 0.3,
        "match_count": 10,
    }).execute()
    print("=== wiki_pages (top 10) ===")
    for r in (res2.data or []):
        cm_preview = (r.get("content_markdown") or "")[:120].replace("\n", " ")
        title = r.get("title", "")
        print(f"  score={r['similarity']:.4f} | {title} | {cm_preview}")


asyncio.run(main())
