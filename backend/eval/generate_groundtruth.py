#!/usr/bin/env python
"""
Helper script — generate ground_truth candidates from the RAG pipeline.

วิธีใช้:
    cd backend
    python -m eval.generate_groundtruth              # company=DEVES
    python -m eval.generate_groundtruth --company DEVES

ผลลัพธ์:
    สร้าง eval/dataset_with_gt.json โดย:
    - คำถามที่มี ground_truth อยู่แล้ว → คงไว้เดิม
    - คำถามที่ยังไม่มี ground_truth    → รัน RAG แล้วใส่คำตอบเป็น candidate

จากนั้นเปิด dataset_with_gt.json แก้ไข/ตรวจสอบให้ถูกต้อง
แล้ว copy ทับ dataset.json เพื่อใช้กับ ragas_eval.py ได้ครบทั้ง 5 metrics
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.retrieval_service import retrieval_service  # noqa: E402
from app.services.chat_service import chat_service            # noqa: E402


async def get_answer(question: str, company_code: str) -> str:
    rows = await retrieval_service.search_context(question, company_code)
    context = chat_service._build_context(rows)
    return await chat_service._generate_answer(
        chat_service._coerce_to_question(question),
        context,
        [],
    )


async def main(company_code: str) -> None:
    dataset_path = Path(__file__).parent / "dataset.json"
    out_path     = Path(__file__).parent / "dataset_with_gt.json"

    with open(dataset_path, encoding="utf-8") as f:
        items: list[dict] = json.load(f)

    print(f"\nGenerating ground_truth candidates for {len(items)} questions ({company_code})\n")

    results = []
    for i, item in enumerate(items, 1):
        q = item["question"]

        # Already has ground_truth — keep as-is
        if "ground_truth" in item:
            print(f"[{i}/{len(items)}] ✓ (existing)  {q[:65]}")
            results.append(item)
            continue

        # Generate candidate from RAG
        print(f"[{i}/{len(items)}] ↻ generating  {q[:65]}")
        try:
            answer = await get_answer(q, company_code)
            print(f"             → {answer[:80].strip()!r}")
            results.append({**item, "ground_truth": answer})
        except Exception as exc:
            print(f"             ✗ error: {exc}")
            results.append(item)  # keep without ground_truth

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    missing = sum(1 for r in results if "ground_truth" not in r)
    print(f"\nSaved → {out_path}")
    print(f"  {len(results) - missing}/{len(results)} questions have ground_truth")
    if missing:
        print(f"  ⚠  {missing} questions still missing ground_truth (check errors above)")
    print()
    print("ขั้นตอนต่อไป:")
    print("  1. เปิด dataset_with_gt.json แล้วตรวจสอบ/แก้ไข ground_truth แต่ละข้อ")
    print("  2. cp eval/dataset_with_gt.json eval/dataset.json")
    print("  3. python -m eval.ragas_eval  ← จะรัน 5 metrics ครบ")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--company", default="DEVES")
    args = parser.parse_args()
    asyncio.run(main(args.company))
