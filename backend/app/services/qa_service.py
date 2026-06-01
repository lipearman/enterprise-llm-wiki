import json
import logging
from app.services.ollama_client import chat_llm, embed_llm
from app.services.provider_service import provider_service, AllProvidersFailedError
from app.core.config import settings
from app.core.text import normalize_question
from app.db.supabase_client import supabase

logger = logging.getLogger(__name__)


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
        messages = [
            {"role": "system", "content": "You generate canonical QA from wiki pages. Return JSON only."},
            {"role": "user", "content": prompt},
        ]
        raw = await self._complete(messages)
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
                # HITL review queue: inactive (pending) until an editor approves.
                "is_active": not settings.ENABLE_REVIEW_QUEUE,
            }
            res = supabase.table("canonical_qa").insert(row).execute()
            saved.append(res.data[0] if res.data else row)
        return saved

    @staticmethod
    async def _complete(messages: list[dict]) -> str:
        """Run via the provider failover chain (role=canonical_qa), falling back
        to the .env chat_llm + QA_GENERATION_MODEL when unconfigured or every
        provider fails."""
        if provider_service.is_configured("canonical_qa"):
            try:
                return await provider_service.chat("canonical_qa", messages, max_tokens=4096)
            except AllProvidersFailedError as exc:
                logger.warning("canonical_qa_providers_failed | falling back to .env | %s", exc)
        return await chat_llm.chat(messages, model=settings.QA_GENERATION_MODEL)

    def _parse_json_array(self, raw: str) -> list[dict]:
        raw = raw.strip()
        start = raw.find("[")
        end = raw.rfind("]")
        if start >= 0 and end >= 0:
            raw = raw[start:end+1]
        return json.loads(raw)

qa_service = QAService()
