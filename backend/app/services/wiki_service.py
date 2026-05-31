import logging
from app.services.ollama_client import chat_llm, embed_llm
from app.services.provider_service import provider_service, AllProvidersFailedError
from app.core.config import settings
from app.core.text import safe_slug
from app.db.supabase_client import supabase

logger = logging.getLogger(__name__)


class WikiService:
    async def generate_wiki_page(self, company_code: str, title: str, facts: dict, source_urls: list[str]) -> dict:
        prompt = f"""
Create an Enterprise LLM Wiki page in Markdown from the facts below.
Rules:
- Write in Thai if content is Thai.
- Be clear, structured, and business-friendly.
- Do not invent facts.
- Include sections: Summary, Key Facts, Procedures, Requirements, Exceptions, Related Entities, Source URLs.

TITLE: {title}
FACTS: {facts}
SOURCE_URLS: {source_urls}
"""
        messages = [
            {"role": "system", "content": "You generate accurate enterprise wiki pages from facts only."},
            {"role": "user", "content": prompt},
        ]
        md = await self._complete(messages)
        emb = await embed_llm.embed(md)
        page = {
            "company_code": company_code,
            "title": title,
            "slug": safe_slug(title),
            "summary": facts.get("summary"),
            "content_markdown": md,
            "source_urls": source_urls,
            "embedding": emb,
            "status": "published",
            "version": 1,
        }
        # Auto-increment version if slug already exists for this company
        slug = page["slug"]
        existing = supabase.table("wiki_pages").select("version").eq("company_code", company_code).eq("slug", slug).order("version", desc=True).limit(1).execute()
        next_version = (existing.data[0]["version"] + 1) if existing.data else 1
        page["version"] = next_version

        res = supabase.table("wiki_pages").insert(page).execute()
        return res.data[0] if res.data else page

    @staticmethod
    async def _complete(messages: list[dict]) -> str:
        """Run via the provider failover chain (role=wiki_generation), falling
        back to the .env chat_llm + WIKI_GENERATION_MODEL when unconfigured or
        every provider fails."""
        if provider_service.is_configured("wiki_generation"):
            try:
                return await provider_service.chat("wiki_generation", messages, max_tokens=6000)
            except AllProvidersFailedError as exc:
                logger.warning("wiki_generation_providers_failed | falling back to .env | %s", exc)
        return await chat_llm.chat(messages, model=settings.WIKI_GENERATION_MODEL)

wiki_service = WikiService()
