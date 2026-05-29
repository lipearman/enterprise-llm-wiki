import logging
import re
from datetime import datetime, timedelta

from app.core.config import settings
from app.core.text import normalize_question
from app.db.supabase_client import supabase
from app.schemas.chat import ChatResponse, ChatSource, SourceRef
from app.services.ollama_client import chat_llm, embed_llm, local_llm
from app.services.retrieval_service import retrieval_service

logger = logging.getLogger(__name__)


# ── Greeting detection ────────────────────────────────────────────────────────
_THAI_POLITE = r"(?:\s*(?:ครับ|ค่ะ|คะ|จ้า|จ้|นะ|นะครับ|นะคะ|ด้วย))?"
_GREETING_PATTERNS = re.compile(
    r"^("
    r"สวัสดี" + _THAI_POLITE + r"|"
    r"หวัดดี" + _THAI_POLITE + r"|"
    r"ดีครับ|ดีค่ะ|ดีจ้า|ดีนะ|"
    r"ฮัลโหล" + _THAI_POLITE + r"|"
    r"เฮลโล่" + _THAI_POLITE + r"|"
    r"ไฮ" + _THAI_POLITE + r"|"
    r"hi|hello|hey|howdy|greetings|"
    r"good\s*(morning|afternoon|evening|day)|"
    r"อรุณสวัสดิ์|สวัสดีตอนเช้า|สวัสดีตอนบ่าย|สวัสดีตอนเย็น"
    r")[\s!?.,]*$",
    re.IGNORECASE,
)

_GREETING_RESPONSE = (
    "สวัสดีครับ! 👋 ผมเป็นผู้ช่วยความรู้ของบริษัท "
    "พร้อมตอบคำถามเกี่ยวกับข้อมูล นโยบาย ผลิตภัณฑ์ และบริการต่าง ๆ\n\n"
    "มีอะไรให้ช่วยไหมครับ?"
)


def _is_greeting(text: str) -> bool:
    return bool(_GREETING_PATTERNS.match(text.strip()))
# ─────────────────────────────────────────────────────────────────────────────


# ── In-memory session store ───────────────────────────────────────────────────
class SessionStore:
    """Stores per-session conversation history in memory.

    Each session holds a list of ``{"role": ..., "content": ...}`` dicts.
    Sessions expire after *ttl_minutes* of inactivity and are capped at
    *max_turns* question-answer pairs to keep token counts manageable.
    """

    def __init__(self, max_turns: int = 10, ttl_minutes: int = 60):
        self._history: dict[str, list[dict]] = {}
        self._touched: dict[str, datetime] = {}
        self.max_turns = max_turns
        self.ttl_minutes = ttl_minutes

    def get(self, session_id: str) -> list[dict]:
        self._evict_expired()
        return list(self._history.get(session_id, []))

    def save(self, session_id: str, question: str, answer: str) -> None:
        if session_id not in self._history:
            self._history[session_id] = []
        self._history[session_id].append({"role": "user",      "content": question})
        self._history[session_id].append({"role": "assistant", "content": answer})
        # Keep only the last max_turns pairs
        cap = self.max_turns * 2
        if len(self._history[session_id]) > cap:
            self._history[session_id] = self._history[session_id][-cap:]
        self._touched[session_id] = datetime.utcnow()

    def clear(self, session_id: str) -> None:
        self._history.pop(session_id, None)
        self._touched.pop(session_id, None)

    def _evict_expired(self) -> None:
        cutoff = datetime.utcnow() - timedelta(minutes=self.ttl_minutes)
        expired = [sid for sid, ts in self._touched.items() if ts < cutoff]
        for sid in expired:
            self._history.pop(sid, None)
            self._touched.pop(sid, None)


session_store = SessionStore(
    max_turns=10,    # remember up to 10 back-and-forth turns
    ttl_minutes=60,  # session expires after 60 min of inactivity
)
# ─────────────────────────────────────────────────────────────────────────────


_NO_ANSWER_PHRASES = [
    "ยังไม่มีข้อมูล",
    "ไม่มีข้อมูลส่วนนี้",
    "ไม่พบข้อมูล",
    "ไม่มีข้อมูลเกี่ยวกับ",
    "ไม่มีข้อมูลในระบบ",
    "ไม่มีในฐานข้อมูล",
]


class ChatService:
    @staticmethod
    def _is_no_answer(answer: str, context_rows: list[dict]) -> bool:
        """Return True when the bot effectively couldn't answer the question.

        Two conditions trigger 'unanswered':
        1. Retrieval returned zero rows → no context at all, LLM had nothing to work with.
        2. LLM explicitly indicated it has no relevant information (sentinel phrases).

        This catches cases where Rule 3 of the prompt ("มีไหม → ไม่มีครับ") makes
        the LLM say "ไม่มีครับ" instead of the full sentinel phrase when context is empty.
        """
        if not context_rows:
            return True
        return any(phrase in answer for phrase in _NO_ANSWER_PHRASES)

    async def answer(
        self,
        question: str,
        company_code: str | None = None,
        force_rag: bool = False,
        session_id: str | None = None,
        track_unanswered: bool = False,
    ) -> ChatResponse:
        company_code = company_code or settings.DEFAULT_COMPANY_CODE

        # Load conversation history for this session (empty list if no session)
        history = session_store.get(session_id) if session_id else []

        # ── Greeting fast-path ────────────────────────────────────────────
        if not force_rag and _is_greeting(question):
            logger.info("greeting_detected | q=%r", question[:40])
            if session_id:
                session_store.save(session_id, question, _GREETING_RESPONSE)
            return ChatResponse(
                answer=_GREETING_RESPONSE,
                mode="greeting",
                cached=False,
                sources=[],
            )

        # ── Build context-aware retrieval query ───────────────────────────
        # When a session has history and the user sends a short follow-up
        # (e.g. just a company name after asking for info), the current
        # question alone gives poor retrieval signal.  We rewrite it into a
        # standalone query that incorporates the conversation context so
        # that retrieval (both canonical QA and RAG) finds the right docs.
        retrieval_q = await self._build_retrieval_query(question, history)

        # ── Answer cache ──────────────────────────────────────────────────
        if not force_rag:
            cached = await retrieval_service.match_answer_cache(retrieval_q, company_code)
            if cached:
                if session_id:
                    session_store.save(session_id, question, cached["answer"])
                return ChatResponse(
                    answer=cached["answer"],
                    mode="answer_cache",
                    cached=True,
                    sources=[],
                )

            # ── Canonical Q&A ─────────────────────────────────────────────
            qa = await retrieval_service.match_canonical_qa(retrieval_q, company_code)
            if qa:
                score = qa.get("similarity", 0)
                logger.info("canonical_qa_used | score=%.4f | answer=%r", score, qa.get("answer", "")[:80])
                if session_id:
                    session_store.save(session_id, question, qa["answer"])
                return ChatResponse(
                    answer=qa["answer"],
                    mode="canonical_qa",
                    cached=False,
                    sources=[ChatSource(
                        source_type="canonical_qa",
                        title=f"[score={score:.3f}] {qa.get('question', '')}",
                        score=score,
                    )],
                )

        # ── RAG ───────────────────────────────────────────────────────────
        context_rows = await retrieval_service.search_context(retrieval_q, company_code)
        context = self._build_context(context_rows)
        # Pass retrieval_q (contextually enriched) to LLM so it knows the
        # full intent even when the user's original message was very short.
        try:
            answer = await self._generate_answer(retrieval_q, context, history)
        except Exception as exc:
            logger.error("llm_generate_error | %s: %s", type(exc).__name__, exc)
            return ChatResponse(
                answer="ขออภัยครับ ขณะนี้ระบบ AI ขัดข้องชั่วคราว กรุณาลองใหม่อีกครั้ง",
                mode="error",
                cached=False,
                source_refs=[],
                sources=[],
            )

        # Save plain answer to history / cache (no source block)
        try:
            await self._save_answer_cache(question, company_code, answer, context_rows)
        except Exception as exc:
            logger.warning("answer_cache_save_error | %s: %s", type(exc).__name__, exc)
        if session_id:
            session_store.save(session_id, question, answer)

        # Don't show source refs when the LLM signals it found nothing useful
        no_answer = "ยังไม่มีข้อมูล" in answer
        source_refs = [] if no_answer else self._build_source_refs(context_rows)

        # Track unanswered questions (floating-chat only)
        if track_unanswered and no_answer:
            await self._save_unanswered_question(question, company_code, session_id)

        return ChatResponse(
            answer=answer,
            mode="rag",
            cached=False,
            source_refs=source_refs,
            sources=[
                ChatSource(
                    source_type=r.get("source_type", "unknown"),
                    title=r.get("title"),
                    url=r.get("source_url"),
                    score=r.get("similarity"),
                )
                for r in context_rows
            ],
        )

    # ── Query rewriting ───────────────────────────────────────────────────────

    async def _build_retrieval_query(self, question: str, history: list[dict]) -> str:
        """Return a retrieval-optimised version of *question*.

        Strategy
        --------
        * No history → return question unchanged.
        * ``ENABLE_QUERY_REWRITE=true`` → call Qwen2.5 to produce a proper
          standalone question (best quality, adds ~1-2 s latency).
        * Fallback → prepend the last user turn so the retrieval embedding
          and text-search carry topic context (fast, no extra LLM call).

        The rewrite is used **only** for retrieval and generation prompt.
        The original question is always stored in session history so the
        conversation log stays natural.
        """
        if not history:
            return question

        if settings.ENABLE_QUERY_REWRITE:
            return await self._rewrite_with_llm(question, history)

        # Fast fallback: concatenate last user turn with current question
        for msg in reversed(history):
            if msg["role"] == "user":
                prev = msg["content"].strip()[:120]
                combined = f"{prev} {question}".strip()
                logger.debug("query_expand_fast | %r → %r", question[:40], combined[:80])
                return combined

        return question

    async def _rewrite_with_llm(self, question: str, history: list[dict]) -> str:
        """Use Qwen2.5 to rewrite a follow-up into a standalone question.

        Example
        -------
        history:  user "ขอที่อยู่หน่อย" / bot "บริษัทอะไรครับ?"
        question: "เทเวศ"
        rewrite:  "ขอที่อยู่สำนักงานของบริษัทเทเวศประกันภัย"
        """
        # Use last 2 turns (4 messages) as context window
        recent = history[-4:]
        ctx_lines = []
        for m in recent:
            role = "ผู้ถาม" if m["role"] == "user" else "บอท"
            ctx_lines.append(f'{role}: {m["content"][:200]}')
        history_text = "\n".join(ctx_lines)

        prompt = (
            f"บทสนทนาก่อนหน้า:\n{history_text}\n\n"
            f'ข้อความล่าสุดของผู้ถาม: "{question}"\n\n'
            "งาน: เขียนข้อความล่าสุดใหม่ให้เป็น **คำถามที่สมบูรณ์ในตัวเอง** "
            "โดยรวม context ที่จำเป็นจากบทสนทนา\n"
            "- ถ้าข้อความล่าสุดสมบูรณ์อยู่แล้ว ให้คืนมาตามเดิม\n"
            "- ตอบเฉพาะคำถามที่เขียนใหม่เท่านั้น ไม่ต้องอธิบาย\n"
            "คำถาม:"
        )
        try:
            rewritten = await local_llm.chat(
                [{"role": "user", "content": prompt}],
                model=settings.CANONICAL_QA_MODEL,
            )
            rewritten = rewritten.strip().strip('"').strip("'")
            if rewritten and len(rewritten) >= len(question):
                logger.info("query_rewrite | %r → %r", question[:50], rewritten[:80])
                return rewritten
        except Exception as exc:
            logger.warning("query_rewrite_error | q=%r | err=%s", question[:50], exc)

        # Fallback to fast concatenation if LLM fails
        for msg in reversed(history):
            if msg["role"] == "user":
                prev = msg["content"].strip()[:120]
                return f"{prev} {question}".strip()

        return question

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_context(self, rows: list[dict]) -> str:
        blocks = []
        for i, r in enumerate(rows, 1):
            content = r.get("content_markdown") or r.get("content") or r.get("answer") or ""
            title = r.get("title") or r.get("source_url") or f"Source {i}"
            blocks.append(f"[Source {i}] {title}\n{content}")
        return "\n\n---\n\n".join(blocks)

    @staticmethod
    def _extract_display_label(title: str) -> str:
        """Extract a clean display label from an enriched title.

        "Deves (About Us - Company Profile)" → "About Us - Company Profile"
        "About Us - Company Profile"          → "About Us - Company Profile"
        "Deves"                               → "" (generic, caller skips)
        """
        m = re.search(r'\(([^)]+)\)\s*$', title)
        if m:
            return m.group(1).strip()
        return title.strip()

    def _build_source_refs(self, rows: list[dict], max_sources: int = 5) -> list[SourceRef]:
        """Build a deduplicated list of SourceRef for frontend display (max 5).

        Skips generic titles ("deves", "unknown", "source").
        Extracts the human-readable part from enriched titles so the
        frontend shows "About Us - Company Profile  [คลิก link]" rather
        than the full "Deves (About Us - Company Profile)".
        """
        seen_labels: set[str] = set()
        refs: list[SourceRef] = []

        for r in rows:
            raw_title = (r.get("title") or "").strip()
            url       = (r.get("source_url") or r.get("url") or "").strip() or None

            # Skip entirely generic titles with no URL fallback
            if not raw_title or raw_title.lower() in {"deves", "unknown", "source"}:
                if not url:
                    continue
                label = url   # fall back to URL as label
            else:
                label = self._extract_display_label(raw_title)
                if not label or label.lower() in {"deves", "unknown", "source"}:
                    # enriched part is still generic → use URL or skip
                    label = url or ""
                if not label:
                    continue

            if label in seen_labels:
                continue
            seen_labels.add(label)

            refs.append(SourceRef(label=label, url=url))
            if len(refs) >= max_sources:
                break

        return refs

    async def answer_stream(
        self,
        question: str,
        company_code: str | None = None,
        force_rag: bool = False,
        session_id: str | None = None,
        track_unanswered: bool = False,
    ):
        """Same pipeline as answer() but streams tokens (async generator).

        Yields dicts:
          {"status": "thinking"}         — heartbeat (keep-alive, no UI change)
          {"token": "<chunk>"}           — one or more LLM token chunks
          {"done": True, "sources": []}  — final event with source refs

        Heartbeats are sent before every slow await so the SSE connection
        stays alive through the Next.js proxy and the browser doesn't time out
        while retrieval / canonical-QA / RAG is still running.
        """
        # ── Heartbeat #0 — sent IMMEDIATELY to establish the SSE connection ──
        # This prevents the Next.js rewrite proxy (and the browser) from
        # cutting the connection before retrieval work even starts.
        yield {"status": "thinking"}

        company_code = company_code or settings.DEFAULT_COMPANY_CODE
        history = session_store.get(session_id) if session_id else []

        # ── Greeting fast-path ────────────────────────────────────────────
        if not force_rag and _is_greeting(question):
            logger.info("stream:greeting_detected | q=%r", question[:40])
            if session_id:
                session_store.save(session_id, question, _GREETING_RESPONSE)
            yield {"token": _GREETING_RESPONSE}
            yield {"done": True, "sources": []}
            return

        # ── Heartbeat #1 — before query-rewrite LLM call (can be slow) ───
        yield {"status": "thinking"}
        retrieval_q = await self._build_retrieval_query(question, history)

        # ── Answer cache ──────────────────────────────────────────────────
        if not force_rag:
            yield {"status": "thinking"}
            cached = await retrieval_service.match_answer_cache(retrieval_q, company_code)
            if cached:
                if session_id:
                    session_store.save(session_id, question, cached["answer"])
                yield {"token": cached["answer"]}
                yield {"done": True, "sources": []}
                return

            # ── Canonical Q&A (may call local LLM for matching) ──────────
            yield {"status": "thinking"}
            qa = await retrieval_service.match_canonical_qa(retrieval_q, company_code)
            if qa:
                if session_id:
                    session_store.save(session_id, question, qa["answer"])
                yield {"token": qa["answer"]}
                yield {"done": True, "sources": []}
                return

        # ── RAG retrieval (embedding + Supabase + text search) ────────────
        yield {"status": "thinking"}
        context_rows = await retrieval_service.search_context(retrieval_q, company_code)
        context = self._build_context(context_rows)

        full_answer = ""
        try:
            async for token in self._generate_answer_stream(retrieval_q, context, history):
                full_answer += token
                yield {"token": token}
        except Exception as exc:
            logger.error("stream:llm_error | %s: %s", type(exc).__name__, exc)
            err = "ขออภัยครับ ขณะนี้ระบบ AI ขัดข้องชั่วคราว กรุณาลองใหม่อีกครั้ง"
            yield {"token": err}
            yield {"done": True, "sources": []}
            return

        # ── Post-stream: session + cache ──────────────────────────────────
        if session_id:
            session_store.save(session_id, question, full_answer)
        try:
            await self._save_answer_cache(question, company_code, full_answer, context_rows)
        except Exception as exc:
            logger.warning("stream:cache_save_error | %s: %s", type(exc).__name__, exc)

        no_answer = "ยังไม่มีข้อมูล" in full_answer
        source_refs = [] if no_answer else self._build_source_refs(context_rows)

        # Track unanswered questions (floating-chat only)
        if track_unanswered and no_answer:
            await self._save_unanswered_question(question, company_code, session_id)

        yield {
            "done": True,
            "sources": [{"title": r.label, "url": r.url} for r in source_refs],
        }

    async def _generate_answer_stream(
        self,
        question: str,
        context: str,
        history: list[dict],
    ):
        """Build prompt and yield tokens from the LLM (async generator)."""
        system_msg = (
            "คุณเป็นผู้ช่วยข้อมูลของบริษัท ตอบได้เฉพาะจากข้อมูลใน CONTEXT ที่ให้มาเท่านั้น "
            "ห้ามใช้ความรู้ทั่วไปหรือข้อมูลนอก CONTEXT เด็ดขาด "
            "คุณจำบทสนทนาก่อนหน้าได้และสามารถอ้างอิงได้"
        )
        current_prompt = f"""กฎเหล็ก (ต้องทำตามทุกข้อ):
1. ตอบได้เฉพาะจาก CONTEXT ด้านล่างเท่านั้น — ห้ามใช้ความรู้ทั่วไปหรือข้อมูลภายนอกเด็ดขาด
2. ถ้า CONTEXT ไม่มีข้อมูลที่เกี่ยวข้องกับคำถาม → ตอบว่า "ขณะนี้ยังไม่มีข้อมูลส่วนนี้ครับ" ทันที ห้ามแต่งคำตอบ
3. ถามว่า "มีไหม / มีหรือเปล่า" → ขึ้นต้นด้วย "มีครับ" หรือ "ไม่มีครับ" แล้วอธิบายจาก CONTEXT
4. ถามว่า "ได้ไหม / ทำได้ไหม" → ขึ้นต้นด้วย "ได้ครับ" หรือ "ไม่ได้ครับ" แล้วอธิบายจาก CONTEXT
5. ถามว่า "ใช่ไหม / จริงไหม" → ขึ้นต้นด้วย "ใช่ครับ" หรือ "ไม่ใช่ครับ"
6. อย่าใช้ประโยค "ไม่พบข้อมูลในฐานความรู้"
7. ถ้าคำถามอ้างอิงบทสนทนาก่อนหน้า ให้ใช้ประวัติด้านบนประกอบการตอบ
8. ถ้าคำถามกว้าง ให้ถามกลับ 1 คำถาม
9. ถ้ามีขั้นตอน ให้เรียงเป็นข้อ
10. ตอบสั้น กระชับ ภาษาสุภาพ เป็นกันเอง

CONTEXT (ใช้ได้เฉพาะข้อมูลจากส่วนนี้เท่านั้น):
{context}

QUESTION: {question}

[ตรวจสอบก่อนตอบ: CONTEXT มีข้อมูลที่ตอบคำถามนี้ได้ไหม? ถ้าไม่มี → ตอบว่า "ขณะนี้ยังไม่มีข้อมูลส่วนนี้ครับ"]"""

        messages: list[dict] = [{"role": "system", "content": system_msg}]
        messages.extend(history)
        messages.append({"role": "user", "content": current_prompt})

        async for token in chat_llm.chat_stream(messages, model=settings.OLLAMA_CHAT_MODEL):
            yield token

    async def _generate_answer(
        self,
        question: str,
        context: str,
        history: list[dict],
    ) -> str:
        system_msg = (
            "คุณเป็นผู้ช่วยข้อมูลของบริษัท ตอบได้เฉพาะจากข้อมูลใน CONTEXT ที่ให้มาเท่านั้น "
            "ห้ามใช้ความรู้ทั่วไปหรือข้อมูลนอก CONTEXT เด็ดขาด "
            "คุณจำบทสนทนาก่อนหน้าได้และสามารถอ้างอิงได้"
        )

        current_prompt = f"""กฎเหล็ก (ต้องทำตามทุกข้อ):
1. ตอบได้เฉพาะจาก CONTEXT ด้านล่างเท่านั้น — ห้ามใช้ความรู้ทั่วไปหรือข้อมูลภายนอกเด็ดขาด
2. ถ้า CONTEXT ไม่มีข้อมูลที่เกี่ยวข้องกับคำถาม → ตอบว่า "ขณะนี้ยังไม่มีข้อมูลส่วนนี้ครับ" ทันที ห้ามแต่งคำตอบ
3. ถามว่า "มีไหม / มีหรือเปล่า" → ขึ้นต้นด้วย "มีครับ" หรือ "ไม่มีครับ" แล้วอธิบายจาก CONTEXT
4. ถามว่า "ได้ไหม / ทำได้ไหม" → ขึ้นต้นด้วย "ได้ครับ" หรือ "ไม่ได้ครับ" แล้วอธิบายจาก CONTEXT
5. ถามว่า "ใช่ไหม / จริงไหม" → ขึ้นต้นด้วย "ใช่ครับ" หรือ "ไม่ใช่ครับ"
6. อย่าใช้ประโยค "ไม่พบข้อมูลในฐานความรู้"
7. ถ้าคำถามอ้างอิงบทสนทนาก่อนหน้า ให้ใช้ประวัติด้านบนประกอบการตอบ
8. ถ้าคำถามกว้าง ให้ถามกลับ 1 คำถาม
9. ถ้ามีขั้นตอน ให้เรียงเป็นข้อ
10. ตอบสั้น กระชับ ภาษาสุภาพ เป็นกันเอง

CONTEXT (ใช้ได้เฉพาะข้อมูลจากส่วนนี้เท่านั้น):
{context}

QUESTION: {question}

[ตรวจสอบก่อนตอบ: CONTEXT มีข้อมูลที่ตอบคำถามนี้ได้ไหม? ถ้าไม่มี → ตอบว่า "ขณะนี้ยังไม่มีข้อมูลส่วนนี้ครับ"]"""

        # Build message list: system → history turns → current question
        messages: list[dict] = [{"role": "system", "content": system_msg}]
        messages.extend(history)   # previous user/assistant turns
        messages.append({"role": "user", "content": current_prompt})

        return await chat_llm.chat(messages, model=settings.OLLAMA_CHAT_MODEL)

    async def _save_unanswered_question(
        self,
        question: str,
        company_code: str,
        session_id: str | None,
    ) -> None:
        """Persist a question the bot couldn't answer so admins can review it."""
        try:
            supabase.table("unanswered_questions").insert({
                "company_code": company_code,
                "question": question,
                "session_id": session_id,
            }).execute()
            logger.info("unanswered_saved | company=%s | q=%r", company_code, question[:80])
        except Exception as exc:
            logger.warning("unanswered_save_error | q=%r | %s: %s", question[:60], type(exc).__name__, exc)

    async def _save_answer_cache(
        self,
        question: str,
        company_code: str,
        answer: str,
        rows: list[dict],
    ) -> None:
        if not settings.ENABLE_ANSWER_CACHE:
            return
        emb = await embed_llm.embed(normalize_question(question))
        source_refs = [
            {"type": r.get("source_type"), "id": r.get("id"), "title": r.get("title"), "url": r.get("source_url")}
            for r in rows
        ]
        supabase.table("answer_cache").upsert({
            "company_code": company_code,
            "question": question,
            "normalized_question": normalize_question(question),
            "answer": answer,
            "embedding": emb,
            "source_refs": source_refs,
        }).execute()


chat_service = ChatService()
