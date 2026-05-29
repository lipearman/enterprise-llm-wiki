"""Add shareholder Q&A to canonical_qa and embed it."""
import sys, io, asyncio, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.ollama_client import embed_llm
from app.core.text import normalize_question
from app.db.supabase_client import supabase

QA_PAIRS = [
    {
        "question": "ผู้ถือหุ้นรายใหญ่ของเทเวศประกันภัยคือใคร",
        "answer": (
            "บริษัท เทเวศประกันภัย จำกัด (มหาชน) มีทุนจดทะเบียน 500 ล้านบาท "
            "ประกอบด้วยหุ้นสามัญ 50 ล้านหุ้น มูลค่าที่ตราไว้หุ้นละ 10 บาท\n\n"
            "โครงสร้างผู้ถือหุ้น:\n"
            "1. พระบาทสมเด็จพระวชิรเกล้าเจ้าอยู่หัว — 49,341,264 หุ้น (98.68%)\n"
            "2. ผู้ถือหุ้นอื่น ๆ — 658,736 หุ้น (1.32%)"
        ),
        "company_code": "DEVES",
        "priority": 1,
        "is_active": True,
    },
    {
        "question": "โครงสร้างผู้ถือหุ้นของเทเวศประกันภัยเป็นอย่างไร",
        "answer": (
            "บริษัท เทเวศประกันภัย จำกัด (มหาชน) มีทุนจดทะเบียน 500 ล้านบาท "
            "ประกอบด้วยหุ้นสามัญ 50 ล้านหุ้น มูลค่าที่ตราไว้หุ้นละ 10 บาท\n\n"
            "โครงสร้างผู้ถือหุ้น:\n"
            "1. พระบาทสมเด็จพระวชิรเกล้าเจ้าอยู่หัว — 49,341,264 หุ้น (98.68%)\n"
            "2. ผู้ถือหุ้นอื่น ๆ — 658,736 หุ้น (1.32%)"
        ),
        "company_code": "DEVES",
        "priority": 1,
        "is_active": True,
    },
]


async def main():
    for qa in QA_PAIRS:
        emb = await embed_llm.embed(normalize_question(qa["question"]))
        row = {**qa, "embedding": emb, "normalized_question": normalize_question(qa["question"])}
        # Check if question already exists
        existing = supabase.table("canonical_qa").select("id").eq("company_code", qa["company_code"]).eq("question", qa["question"]).execute()
        if existing.data:
            rid = existing.data[0]["id"]
            res = supabase.table("canonical_qa").update({"answer": qa["answer"], "embedding": emb}).eq("id", rid).execute()
            print(f"Updated: {qa['question'][:60]}")
        else:
            res = supabase.table("canonical_qa").insert(row).execute()
            print(f"Inserted: {qa['question'][:60]} -> {len(res.data)} row(s)")
    print("Done.")


asyncio.run(main())
