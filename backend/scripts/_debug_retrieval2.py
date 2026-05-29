"""Debug: find Shareholder page score and fix retrieval."""
import sys, io, asyncio, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.ollama_client import embed_llm
from app.core.text import normalize_question
from app.db.supabase_client import supabase


async def main():
    question = "ผู้ถือหุ้นรายใหญ่ของเทเวศประกันภัยคือใคร"
    q_emb = await embed_llm.embed(normalize_question(question))

    # Get ALL wiki_pages with low threshold to find Shareholder page score
    res = supabase.rpc("match_wiki_pages", {
        "query_embedding": q_emb,
        "match_company_code": "DEVES",
        "match_threshold": 0.1,
        "match_count": 40,
    }).execute()
    print("=== ALL wiki_pages (threshold=0.1) ===")
    for r in (res.data or []):
        title = r.get("title", "")
        print(f"  score={r['similarity']:.4f} | {title}")

    print()

    # Get ALL document_chunks with low threshold
    res2 = supabase.rpc("match_document_chunks", {
        "query_embedding": q_emb,
        "match_company_code": "DEVES",
        "match_threshold": 0.4,
        "match_count": 30,
    }).execute()
    print("=== document_chunks (threshold=0.4, top 30) ===")
    for r in (res2.data or []):
        content_preview = (r.get("content") or "")[:100].replace("\n", " ")
        print(f"  score={r['similarity']:.4f} | {content_preview}")


asyncio.run(main())
