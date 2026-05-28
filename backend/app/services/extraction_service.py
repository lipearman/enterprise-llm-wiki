import json
from app.services.ollama_client import chat_llm
from app.core.config import settings


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
        raw = await chat_llm.chat([
            {"role": "system", "content": "You extract structured facts. Return valid JSON only."},
            {"role": "user", "content": prompt},
        ], model=settings.FACT_EXTRACTION_MODEL)
        return self._parse_json(raw)

    def _parse_json(self, raw: str) -> dict:
        raw = raw.strip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end >= 0:
            raw = raw[start:end+1]
        return json.loads(raw)

extraction_service = ExtractionService()
