from app.core.config import settings
from app.core.text import normalize_question
from app.db.supabase_client import supabase
from app.schemas.chat import ChatResponse, ChatSource
from app.services.ollama_client import chat_llm, embed_llm
from app.services.retrieval_service import retrieval_service


class ChatService:
    async def answer(self, question: str, company_code: str | None = None, force_rag: bool = False) -> ChatResponse:
        company_code = company_code or settings.DEFAULT_COMPANY_CODE

        if not force_rag:
            cached = await retrieval_service.match_answer_cache(question, company_code)
            if cached:
                return ChatResponse(answer=cached["answer"], mode="answer_cache", cached=True, sources=[])

            qa = await retrieval_service.match_canonical_qa(question, company_code)
            if qa:
                return ChatResponse(
                    answer=qa["answer"],
                    mode="canonical_qa",
                    cached=False,
                    sources=[ChatSource(source_type="canonical_qa", title=qa.get("question"), score=qa.get("similarity"))],
                )

        context_rows = await retrieval_service.search_context(question, company_code)
        context = self._build_context(context_rows)
        answer = await self._generate_answer(question, context)
        await self._save_answer_cache(question, company_code, answer, context_rows)
        return ChatResponse(
            answer=answer,
            mode="rag",
            cached=False,
            sources=[ChatSource(source_type=r.get("source_type", "unknown"), title=r.get("title"), url=r.get("source_url"), score=r.get("similarity")) for r in context_rows],
        )

    def _build_context(self, rows: list[dict]) -> str:
        blocks = []
        for i, r in enumerate(rows, 1):
            content = r.get("content_markdown") or r.get("content") or r.get("answer") or ""
            title = r.get("title") or r.get("source_url") or f"Source {i}"
            blocks.append(f"[Source {i}] {title}\n{content}")
        return "\n\n---\n\n".join(blocks)

    async def _generate_answer(self, question: str, context: str) -> str:
        prompt = f"""
คุณเป็นผู้ช่วยความรู้ของบริษัท ตอบเหมือนเจ้าหน้าที่ที่เข้าใจงานจริง

กฎ:
1. ตอบจาก CONTEXT เท่านั้น
2. ห้ามแต่งข้อมูลเพิ่ม
3. ถ้าข้อมูลไม่พอ ให้บอกว่าไม่พบข้อมูลในฐานความรู้
4. ถ้าคำถามกว้าง ให้ถามกลับ 1 คำถาม
5. ใช้ภาษาไทยสุภาพ เป็นธรรมชาติ
6. ตอบสั้น กระชับ เข้าใจง่าย
7. ถ้ามีขั้นตอน ให้เรียงเป็นข้อ

QUESTION:
{question}

CONTEXT:
{context}
"""
        return await chat_llm.chat([
            {"role": "system", "content": "You are a grounded enterprise knowledge assistant."},
            {"role": "user", "content": prompt},
        ], model=settings.OLLAMA_CHAT_MODEL)

    async def _save_answer_cache(self, question: str, company_code: str, answer: str, rows: list[dict]) -> None:
        if not settings.ENABLE_ANSWER_CACHE:
            return
        emb = await embed_llm.embed(normalize_question(question))
        source_refs = [{"type": r.get("source_type"), "id": r.get("id"), "title": r.get("title"), "url": r.get("source_url")} for r in rows]
        supabase.table("answer_cache").upsert({
            "company_code": company_code,
            "question": question,
            "normalized_question": normalize_question(question),
            "answer": answer,
            "embedding": emb,
            "source_refs": source_refs,
        }).execute()

chat_service = ChatService()
