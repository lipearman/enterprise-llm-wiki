import json
import logging
from app.services.ollama_client import chat_llm
from app.services.provider_service import provider_service, AllProvidersFailedError
from app.core.config import settings

logger = logging.getLogger(__name__)


class ExtractionService:
    async def extract_facts(self, title: str, content: str) -> dict:
        prompt = f"""
Extract factual knowledge from the content below.
Return JSON only with this schema:
{{
  "title": string,
  "summary": string,
  "key_facts": [string],
  "procedures": [string],
  "requirements": [string],
  "exceptions": [string],
  "entities": [{{"name": string, "type": string, "description": string}}]
}}
Rules:
- Do not invent facts.
- If data is missing, use empty arrays.
- Keep Thai content in Thai.

TITLE: {title}
CONTENT:
{content[:12000]}
"""
        messages = [
            {"role": "system", "content": "You extract structured facts. Return valid JSON only."},
            {"role": "user", "content": prompt},
        ]
        raw = await self._complete(messages)
        return self._parse_json(raw)

    @staticmethod
    async def _complete(messages: list[dict]) -> str:
        """Run via the provider failover chain (role=fact_extraction), falling
        back to the .env chat_llm + FACT_EXTRACTION_MODEL when unconfigured or
        every provider fails."""
        if provider_service.is_configured("fact_extraction"):
            try:
                return await provider_service.chat("fact_extraction", messages, max_tokens=4096)
            except AllProvidersFailedError as exc:
                logger.warning("fact_extraction_providers_failed | falling back to .env | %s", exc)
        return await chat_llm.chat(messages, model=settings.FACT_EXTRACTION_MODEL)

    def _parse_json(self, raw: str) -> dict:
        raw = raw.strip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end >= 0:
            raw = raw[start:end+1]
        return json.loads(raw)

extraction_service = ExtractionService()
