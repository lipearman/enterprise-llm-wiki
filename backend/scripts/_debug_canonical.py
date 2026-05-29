"""Debug: check canonical_qa similarity scores for various questions."""
import sys, io, asyncio, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.ollama_client import embed_llm
from app.core.text import normalize_question
from app.db.supabase_client import supabase


async def main():
    questions = [
        "ผู้ถือหุ้นรายใหญ่ของเทเวศประกันภัยคือใคร",   # exact match expected
        "โครงสร้างผู้ถือหุ้นของเทเวศประกันภัยเป็นอย่างไร",  # near-match expected
        "วิธีเคลมประกันรถยนต์",                         # unrelated — should NOT match
        "สาขาของเทเวศประกันภัยมีที่ไหนบ้าง",            # unrelated — should NOT match
        "ทุนจดทะเบียนของเทเวศประกันภัยเท่าไหร่",        # somewhat related
    ]

    for q in questions:
        q_emb = await embed_llm.embed(normalize_question(q))
        res = supabase.rpc("match_canonical_qa", {
            "query_embedding": q_emb,
            "match_company_code": "DEVES",
            "match_threshold": 0.70,
            "match_count": 3,
        }).execute()
        print(f"Q: {q}")
        if res.data:
            for hit in res.data:
                print(f"  score={hit['similarity']:.4f} | {hit['question'][:60]}")
        else:
            print("  (no matches >= 0.70)")
        print()


asyncio.run(main())
