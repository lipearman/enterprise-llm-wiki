from app.core.config import settings
from app.core.text import normalize_question, sha256_text
from app.services.ollama_client import embed_llm
from app.db.supabase_client import supabase


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
        rows.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        return rows[: settings.RERANK_TOP_K]

    def cache_key(self, question: str, company_code: str) -> str:
        return sha256_text(company_code + "|" + normalize_question(question))

retrieval_service = RetrievalService()
