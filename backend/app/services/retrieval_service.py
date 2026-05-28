import logging
from app.core.config import settings
from app.core.text import normalize_question, sha256_text
from app.services.ollama_client import embed_llm
from app.db.supabase_client import supabase

logger = logging.getLogger(__name__)


class RetrievalService:
    async def query_embedding(self, question: str) -> list[float]:
        return await embed_llm.embed(normalize_question(question))

    async def match_answer_cache(self, question: str, company_code: str) -> dict | None:
        if not settings.ENABLE_ANSWER_CACHE:
            return None
        q_emb = await self.query_embedding(question)
        res = supabase.rpc("match_answer_cache", {
            "query_embedding": q_emb,
            "match_company_code": company_code,
            "match_threshold": settings.ANSWER_CACHE_THRESHOLD,
            "match_count": 1,
        }).execute()
        return res.data[0] if res.data else None

    async def match_canonical_qa(self, question: str, company_code: str) -> dict | None:
        if not settings.ENABLE_CANONICAL_QA:
            return None
        q_emb = await self.query_embedding(question)
        res = supabase.rpc("match_canonical_qa", {
            "query_embedding": q_emb,
            "match_company_code": company_code,
            "match_threshold": settings.CANONICAL_THRESHOLD,
            "match_count": 1,
        }).execute()
        return res.data[0] if res.data else None

    async def search_context(self, question: str, company_code: str) -> list[dict]:
        q_emb = await self.query_embedding(question)
        rows = []
        if settings.ENABLE_WIKI_SEARCH:
            res = supabase.rpc("match_wiki_pages", {
                "query_embedding": q_emb,
                "match_company_code": company_code,
                "match_threshold": settings.SIMILARITY_THRESHOLD,
                "match_count": settings.RETRIEVAL_TOP_K,
            }).execute()
            rows.extend([{**x, "source_type": "wiki"} for x in (res.data or [])])
        if settings.ENABLE_CHUNK_SEARCH:
            res = supabase.rpc("match_document_chunks", {
                "query_embedding": q_emb,
                "match_company_code": company_code,
                "match_threshold": settings.SIMILARITY_THRESHOLD,
                "match_count": settings.RETRIEVAL_TOP_K,
            }).execute()
            rows.extend([{**x, "source_type": "chunk"} for x in (res.data or [])])

        # Graph expansion: find related wiki pages via relationships
        if settings.ENABLE_RELATIONSHIP_SEARCH and rows:
            related = await self._expand_via_relationships(rows, company_code, q_emb)
            # Add related rows not already in results
            existing_ids = {r.get("id") for r in rows}
            for r in related:
                if r.get("id") not in existing_ids:
                    rows.append(r)
                    existing_ids.add(r.get("id"))

        rows.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        return rows[: settings.RERANK_TOP_K]

    async def _expand_via_relationships(
        self, base_rows: list[dict], company_code: str, q_emb: list[float]
    ) -> list[dict]:
        """Expand context by following wiki_relationships edges from found pages."""
        from app.services.relationship_service import relationship_service

        # Collect entity names from top wiki pages found so far
        top_wiki = [r for r in base_rows if r.get("source_type") == "wiki"][:3]
        entities = [r.get("title", "") for r in top_wiki if r.get("title")]
        if not entities:
            return []

        # Find related entities from graph
        graph_rows = relationship_service.find_related_entities(company_code, entities)
        if not graph_rows:
            return []

        # Collect unique related entity names
        related_entities: set[str] = set()
        for gr in graph_rows:
            related_entities.add(gr["source_entity"])
            related_entities.add(gr["target_entity"])
        # Remove already-known entities
        related_entities -= set(entities)

        # Fetch wiki pages whose title matches related entities
        extra_rows: list[dict] = []
        for entity in list(related_entities)[:5]:
            try:
                res = supabase.table("wiki_pages").select(
                    "id,title,slug,content_markdown,source_urls"
                ).eq("company_code", company_code).ilike("title", f"%{entity}%").limit(2).execute()
                for page in (res.data or []):
                    extra_rows.append({
                        **page,
                        "source_type": "wiki_relationship",
                        "similarity": 0.5,   # lower priority than direct vector match
                    })
            except Exception as e:
                logger.warning(f"Relationship expand failed for entity '{entity}': {e}")

        return extra_rows

    def cache_key(self, question: str, company_code: str) -> str:
        return sha256_text(company_code + "|" + normalize_question(question))

retrieval_service = RetrievalService()
