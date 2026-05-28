from app.core.config import settings
from app.core.text import sha256_text
from app.core.logging import logger
from app.db.supabase_client import supabase
from app.services.crawler_service import crawler_service
from app.services.chunking_service import chunking_service
from app.services.extraction_service import extraction_service
from app.services.ollama_client import embed_llm
from app.services.wiki_service import wiki_service
from app.services.qa_service import qa_service
from app.services.relationship_service import relationship_service


class IngestPipeline:
    async def ingest_url(
        self,
        url: str,
        company_code: str | None = None,
        run_deep_enrichment: bool = True,
        crawler_backend: str | None = None,
    ) -> dict:
        company_code = company_code or settings.DEFAULT_COMPANY_CODE
        doc = await crawler_service.fetch_url(url, backend=crawler_backend)
        source = self._upsert_source(company_code, "url", url, doc["title"])

        # Change detection: skip heavy processing if content unchanged
        changed, page = self._upsert_source_page(company_code, source["id"], url, doc["title"], doc["content_markdown"])
        if not changed:
            logger.info(f"Skipped (unchanged): {url}")
            return {"source": source, "page": page, "chunks": 0, "status": "unchanged"}

        chunks = await self._save_chunks(company_code, page["id"], url, doc["title"], doc["content_markdown"])
        result = {"source": source, "page": page, "chunks": len(chunks), "status": "searchable"}

        if run_deep_enrichment:
            wiki = await self.deep_enrich(company_code, doc["title"], doc["content_markdown"], [url])
            result["wiki_page"] = wiki.get("wiki_page")
            result["canonical_qa_count"] = len(wiki.get("canonical_qa", []))
            result["relationships_count"] = len(wiki.get("relationships", []))
            result["status"] = "enriched"
        return result

    async def ingest_file(self, file_path: str, company_code: str | None = None, run_deep_enrichment: bool = True) -> dict:
        """Ingest a local file (PDF, DOCX, XLSX, TXT)."""
        from app.services.file_loader_service import file_loader_service
        company_code = company_code or settings.DEFAULT_COMPANY_CODE
        doc = file_loader_service.load_file(file_path)
        fake_url = f"file://{file_path}"
        source = self._upsert_source(company_code, "file", fake_url, doc["title"])

        changed, page = self._upsert_source_page(company_code, source["id"], fake_url, doc["title"], doc["content_markdown"])
        if not changed:
            return {"source": source, "page": page, "chunks": 0, "status": "unchanged"}

        chunks = await self._save_chunks(company_code, page["id"], fake_url, doc["title"], doc["content_markdown"])
        result = {"source": source, "page": page, "chunks": len(chunks), "status": "searchable"}

        if run_deep_enrichment:
            wiki = await self.deep_enrich(company_code, doc["title"], doc["content_markdown"], [fake_url])
            result["wiki_page"] = wiki.get("wiki_page")
            result["canonical_qa_count"] = len(wiki.get("canonical_qa", []))
            result["relationships_count"] = len(wiki.get("relationships", []))
            result["status"] = "enriched"
        return result

    def _enrich_title(self, title: str, source_urls: list[str]) -> str:
        """Derive a meaningful title from URL path when page title is too generic."""
        if not source_urls:
            return title
        url = source_urls[0]
        if url.startswith("file://"):
            return title
        try:
            from urllib.parse import urlparse
            path = urlparse(url).path.strip("/")
            parts = [p for p in path.split("/") if p and p not in ("th", "en")]
            if parts:
                label = " - ".join(p.replace("-", " ").title() for p in parts[-2:])
                return f"{title} ({label})" if title and title.lower() not in label.lower() else label
        except Exception:
            pass
        return title

    async def deep_enrich(self, company_code: str, title: str, content: str, source_urls: list[str]) -> dict:
        title = self._enrich_title(title, source_urls)
        facts = await extraction_service.extract_facts(title, content)
        fact_res = supabase.table("extracted_facts").insert({
            "company_code": company_code,
            "title": title,
            "facts_json": facts,
            "source_urls": source_urls,
        }).execute()
        wiki_page = await wiki_service.generate_wiki_page(company_code, title, facts, source_urls)
        canonical_qa = await qa_service.generate_canonical_qa(company_code, wiki_page.get("id"), wiki_page.get("content_markdown", ""))
        relationships: list[dict] = []
        if settings.ENABLE_RELATIONSHIP_SEARCH:
            relationships = await relationship_service.extract_relationships(
                company_code=company_code,
                wiki_page_id=wiki_page.get("id"),
                title=title,
                content=wiki_page.get("content_markdown", ""),
            )
        return {
            "facts": fact_res.data[0] if fact_res.data else facts,
            "wiki_page": wiki_page,
            "canonical_qa": canonical_qa,
            "relationships": relationships,
        }

    def _upsert_source(self, company_code: str, source_type: str, source_url: str, source_name: str) -> dict:
        res = supabase.table("knowledge_sources").upsert({
            "company_code": company_code,
            "source_type": source_type,
            "source_url": source_url,
            "source_name": source_name,
            "is_active": True,
        }, on_conflict="company_code,source_url").execute()
        return res.data[0]

    def _upsert_source_page(self, company_code: str, source_id: str, url: str, title: str, content: str) -> tuple[bool, dict]:
        """Returns (changed, page_row). If content hash unchanged, changed=False."""
        content_hash = sha256_text(content)

        # Check existing hash
        existing = supabase.table("source_pages").select("id,content_hash").eq("company_code", company_code).eq("url", url).limit(1).execute()
        if existing.data and existing.data[0].get("content_hash") == content_hash:
            return False, existing.data[0]

        res = supabase.table("source_pages").upsert({
            "company_code": company_code,
            "source_id": source_id,
            "url": url,
            "title": title,
            "content_markdown": content,
            "content_hash": content_hash,
        }, on_conflict="company_code,url").execute()
        return True, res.data[0]

    async def _save_chunks(self, company_code: str, source_page_id: str, url: str, title: str, content: str) -> list[dict]:
        # Delete old chunks for this page first
        supabase.table("document_chunks").delete().eq("company_code", company_code).eq("source_url", url).execute()

        chunks = chunking_service.split(content)
        saved = []
        for idx, chunk in enumerate(chunks):
            emb = await embed_llm.embed(chunk)
            res = supabase.table("document_chunks").insert({
                "company_code": company_code,
                "source_page_id": source_page_id,
                "source_url": url,
                "title": title,
                "chunk_index": idx,
                "content": chunk,
                "embedding": emb,
            }).execute()
            saved.extend(res.data or [])
        return saved


ingest_pipeline = IngestPipeline()
