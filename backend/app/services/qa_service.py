import json
from app.services.ollama_client import chat_llm, embed_llm
from app.core.config import settings
from app.core.text import normalize_question
from app.db.supabase_client import supabase


class QAService:
    async def generate_canonical_qa(self, company_code: str, wiki_page_id: str, wiki_markdown: str) -> list[dict]:
        prompt = f"""
Generate canonical FAQ pairs from this wiki page.
Return JSON array only:
[
  {{"question": string, "answer": string, "priority": number}}
]
Rules:
- Do not invent beyond the wiki page.
- Answers must be stable and concise.
- Generate 5-10 useful questions.

WIKI:
{wiki_markdown[:12000]}
"""
        raw = await chat_llm.chat([
            {"role": "system", "content": "You generate canonical QA from wiki pages. Return JSON only."},
            {"role": "user", "content": prompt},
        ], model=settings.QA_GENERATION_MODEL)
        qa_items = self._parse_json_array(raw)
        saved = []
        for item in qa_items:
            q = item["question"]
            a = item["answer"]
            emb = await embed_llm.embed(normalize_question(q))
            row = {
                "company_code": company_code,
                "wiki_page_id": wiki_page_id,
                "question": q,
                "normalized_question": normalize_question(q),
                "answer": a,
                "priority": int(item.get("priority", 100)),
                "embedding": emb,
                "is_active": True,
            }
            res = supabase.table("canonical_qa").insert(row).execute()
            saved.append(res.data[0] if res.data else row)
        return saved

    def _parse_json_array(self, raw: str) -> list[dict]:
        raw = raw.strip()
        start = raw.find("[")
        end = raw.rfind("]")
        if start >= 0 and end >= 0:
            raw = raw[start:end+1]
        return json.loads(raw)

qa_service = QAService()
