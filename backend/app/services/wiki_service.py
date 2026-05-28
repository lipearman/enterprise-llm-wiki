from app.services.ollama_client import chat_llm, embed_llm
from app.core.config import settings
from app.core.text import safe_slug
from app.db.supabase_client import supabase


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
        md = await chat_llm.chat([
            {"role": "system", "content": "You generate accurate enterprise wiki pages from facts only."},
            {"role": "user", "content": prompt},
        ], model=settings.WIKI_GENERATION_MODEL)
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

wiki_service = WikiService()
