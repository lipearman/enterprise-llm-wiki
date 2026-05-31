import logging
import re
from datetime import datetime, timedelta

from app.core.config import settings
from app.core.text import normalize_question
from app.db.supabase_client import supabase
from app.schemas.chat import ChatResponse, ChatSource, SourceRef
from app.services.ollama_client import chat_llm, embed_llm, local_llm
from app.services.retrieval_service import retrieval_service
from app.services.bot_settings_service import bot_settings_service

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

# Phrases that indicate the bot asked a clarifying question.
# These should NOT be saved as unanswered — the conversation is still in progress.
_CLARIFY_PHRASES = [
    "หมายถึงอะไรครับ",
    "หมายถึงอะไรคะ",
    "ต้องการข้อมูลส่วนไหน",
    "ต้องการทราบข้อมูลส่วนไหน",
    "กรุณาระบุเพิ่มเติม",
    "ขอทราบเพิ่มเติม",
]

# ── Python-level ambiguity detection ─────────────────────────────────────────
# Keywords that are genuinely ambiguous in an insurance-company context.
# Each maps to a list of predefined sub-type choices shown to the user.
_AMBIGUOUS_KEYWORDS: dict[str, list[str]] = {
    "เบอร์":   ["เบอร์โทรศัพท์", "เบอร์กรมธรรม์", "เบอร์เคลม", "เบอร์มือถือ"],
    "รหัส":   ["รหัสกรมธรรม์", "รหัสอ้างอิง", "รหัสสาขา"],
    "ราคา":   ["ราคาเบี้ยประกัน", "ราคาซ่อม", "ราคาต่ออายุ"],
    "ติดต่อ": ["ช่องทางโทรศัพท์", "ช่องทางอีเมล", "ที่อยู่สำนักงาน"],
    "ที่อยู่": ["ที่อยู่สำนักงานใหญ่", "ที่อยู่สาขา"],
    "เอกสาร": ["เอกสารการเคลม", "เอกสารต่อกรมธรรม์", "เอกสารใบแจ้งหนี้"],
}

# Specific question words that signal CLEAR intent — even if the question
# also contains an ambiguous keyword, these take priority.
_CLEAR_QUESTION_WORDS = [
    "ที่ไหน", "อยู่ที่ไหน", "ได้ที่ไหน",
    "อย่างไร", "ยังไง",
    "คืออะไร", "หมายความว่าอะไร",
    "ทำอะไร", "ทำได้ไหม", "ทำยังไง",
    "เมื่อไหร่", "เท่าไหร่", "กี่บาท",
    "คือใคร", "มีไหม", "ใช่ไหม",
]


class ChatService:

    def _build_clarify_response(
        self, question: str, context_rows: list[dict], company_code: str
    ) -> str | None:
        """Return a pre-built clarifying question when the question contains an
        ambiguous keyword AND the question has no clear-intent word.

        Called BEFORE the LLM so we never rely on the model to detect ambiguity.
        Always uses PREDEFINED choices (from DB config), never LLM-generated ones,
        so the choices are always the correct subtypes of the keyword — not random
        context topics that the LLM might incorrectly associate.

        NOTE: context_rows is intentionally ignored for the ambiguous-keyword check.
        Even when context has data, we still ask the predefined clarifying question
        so the user picks a specific subtype ("เบอร์โทรศัพท์") rather than the bot
        offering unrelated context topics (e.g. "ที่อยู่สำนักงาน") as fake subtypes.

        Returns None when:
        - question contains a clear question word (ที่ไหน / คืออะไร / etc.)
        - question uses a compound/specific term that removes ambiguity
        - no ambiguous keyword found  →  let LLM answer from context
        """
        q = question.strip()

        # Load per-company config (cached after first load)
        clear_words  = bot_settings_service.get(company_code, "clear_question_words")
        ambiguous_kw = bot_settings_service.get(company_code, "ambiguous_keywords")

        # Clear question words → not ambiguous regardless of keywords
        for clear_word in clear_words:
            if clear_word in q:
                return None

        # Compound/specific terms override single-keyword ambiguity
        # e.g. "เบอร์กรมธรรม์" is specific even though it contains "เบอร์"
        compound_overrides = [
            "เบอร์กรมธรรม์", "เบอร์ติดต่อ", "เบอร์โทรศัพท์",
            "รหัสกรมธรรม์", "รหัสอ้างอิง",
            "ราคาเบี้ย", "ที่อยู่สำนักงาน",
        ]
        for compound in compound_overrides:
            if compound in q:
                return None

        # Match ambiguous keyword → ALWAYS return predefined choices
        for keyword, choices in ambiguous_kw.items():
            if keyword in q:
                # If the user already specified one of the known sub-types
                # (e.g. answered "ที่อยู่สาขา" after a clarification prompt),
                # treat the question as specific enough → don't ask again.
                if any(choice in q for choice in choices):
                    return None
                # If the question carries substantial specific context beyond the
                # keyword and common filler, the user has already expressed clear
                # intent (e.g. "เอกสารที่ต้องใช้ในการซื้อประกันรถยนต์") → answer
                # from context instead of asking a needless clarifying question.
                if self._has_specific_context(q, keyword):
                    return None
                bullets = "\n".join(f"• {c}" for c in choices)
                return (
                    f'"{keyword}" หมายถึงอะไรครับ?\n'
                    f'{bullets}\n'
                    f'ต้องการข้อมูลส่วนไหนครับ?'
                )

        return None

    # Common Thai particles / filler that carry no disambiguating intent.
    _FILLER_TOKENS = (
        "เอกสาร", "ที่", "ต้อง", "ใช้", "ใน", "การ", "มี", "อะไร", "บ้าง",
        "ของ", "หน่อย", "ขอ", "ครับ", "คะ", "ค่ะ", "จะ", "ได้", "เป็น",
        "และ", "หรือ", "กับ", "ให้", "อยาก", "ช่วย", "ทราบ", "อยาก",
    )

    @classmethod
    def _has_specific_context(cls, question: str, keyword: str) -> bool:
        """True when the question carries specific intent beyond *keyword*.

        Strips the ambiguous keyword and common Thai filler, then checks whether
        meaningful content remains. A bare query like "ขอเอกสารหน่อย" reduces to
        nothing (→ still ambiguous), while "เอกสารที่ต้องใช้ในการซื้อประกันรถยนต์"
        leaves "ซื้อประกันรถยนต์" (→ specific, skip the clarifying question).
        """
        remainder = question.replace(keyword, "")
        for tok in cls._FILLER_TOKENS:
            remainder = remainder.replace(tok, "")
        remainder = "".join(remainder.split())
        # ≥ 9 Thai characters of leftover content ≈ at least one real topic word.
        return len(remainder) >= 9

    def _is_no_answer(self, answer: str, context_rows: list[dict], company_code: str) -> bool:
        """Return True when the bot effectively couldn't answer the question.

        Two conditions trigger 'unanswered':
        1. Retrieval returned zero rows → no context at all, LLM had nothing to work with.
        2. LLM explicitly indicated it has no relevant information (sentinel phrases).

        Clarifying questions ("หมายถึงอะไรครับ?") are NOT counted as unanswered —
        the conversation is ongoing and the user just needs to specify more detail.
        Phrase lists are loaded from BotSettingsService (DB-backed, editable via UI).
        """
        clarify_phrases  = bot_settings_service.get(company_code, "clarify_phrases")
        no_answer_phrases = bot_settings_service.get(company_code, "no_answer_phrases")

        # Clarifying question → still in progress, don't save as unanswered
        if any(phrase in answer for phrase in clarify_phrases):
            return False
        if not context_rows:
            return True
        return any(phrase in answer for phrase in no_answer_phrases)

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

        # ── Python-level ambiguity check (BEFORE cache/QA — always deterministic) ──
        # Must run first so ambiguous keywords always trigger the predefined
        # clarifying question and never get served a stale cached answer.
        clarify = self._build_clarify_response(question, [], company_code)
        if clarify:
            logger.info("clarify_intercept | q=%r | kw_match=True", question[:60])
            if session_id:
                session_store.save(session_id, question, clarify)
            return ChatResponse(
                answer=clarify,
                mode="rag",
                cached=False,
                source_refs=[],
                sources=[],
            )

        # ── Build context-aware retrieval query (RAG only) ───────────────
        # retrieval_q enriches short follow-ups (e.g. "LOCKTON" after
        # "ขอที่อยู่") for the vector search step ONLY.
        # Cache / canonical QA / the LLM prompt always use the original
        # question so previous-turn content cannot contaminate the answer.
        retrieval_q = await self._build_retrieval_query(question, history)

        # ── Answer cache — use original question to avoid history bleed ───
        if not force_rag:
            cached = await retrieval_service.match_answer_cache(question, company_code)
            if cached:
                if session_id:
                    session_store.save(session_id, question, cached["answer"])
                return ChatResponse(
                    answer=cached["answer"],
                    mode="answer_cache",
                    cached=True,
                    sources=[],
                )

            # ── Canonical Q&A — use original question ─────────────────────
            qa = await retrieval_service.match_canonical_qa(question, company_code)
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

        # ── RAG — retrieval_q (enriched) for embedding, original for LLM ──
        context_rows = await retrieval_service.search_context(retrieval_q, company_code)

        context = self._build_context(context_rows)
        # Use the original question in the LLM prompt so history from
        # the previous turn does not distort what the model answers.
        try:
            answer = await self._generate_answer(self._coerce_to_question(question), context, history)
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
        no_answer = self._is_no_answer(answer, context_rows, company_code)
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

    @staticmethod
    def _coerce_to_question(question: str) -> str:
        """If the question is a bare noun-phrase (topic name without any verb or
        question word), rewrite it so the LLM knows to summarise the topic.

        Examples:
          "ประกันรถยนต์"  → "ขอข้อมูลเกี่ยวกับประกันรถยนต์"
          "เบอร์โทรศัพท์" → "ขอข้อมูลเกี่ยวกับเบอร์โทรศัพท์"
          "ขอเบอร์หน่อย"  → unchanged  (has verb "ขอ")
          "ซื้อประกันที่ไหน" → unchanged (has question word "ที่ไหน")
        """
        _QUESTION_WORDS = [
            "ที่ไหน", "อยู่ที่ไหน", "ได้ที่ไหน", "อย่างไร", "ยังไง",
            "คืออะไร", "หมายความว่า", "ทำอะไร", "ทำได้ไหม", "ทำยังไง",
            "เมื่อไหร่", "เท่าไหร่", "กี่บาท", "คือใคร",
            "มีไหม", "ใช่ไหม", "จริงไหม", "หรือเปล่า", "บ้าง",
            # common question/sentence-final particles
            "ไหม", "หน่อย", "นะ", "ด้วย", "เลย",
        ]
        _VERB_PREFIXES = [
            "ขอ", "ต้องการ", "อยาก", "ช่วย", "บอก", "แจ้ง",
            "ส่ง", "ดู", "เช็ค", "ทำ", "จอง", "สมัคร",
            "ชำระ", "ต่อ", "ยกเลิก", "ซื้อ", "เปิด", "ปิด",
        ]
        q = question.strip()
        # Has a question word anywhere → already a question
        for w in _QUESTION_WORDS:
            if w in q:
                return question
        # Starts with or contains a common Thai verb → already a request
        for v in _VERB_PREFIXES:
            if v in q:
                return question
        # Bare noun-phrase → append "มีอะไรบ้าง" so the LLM prompt's
        # clear-question-word bypass ("บ้าง") kicks in, forcing a direct answer.
        return f"{q}มีอะไรบ้าง"

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

        try:
            # ── Python-level ambiguity check (BEFORE cache — always deterministic) ──
            # Must run first so ambiguous keywords always trigger the predefined
            # clarifying question and never get served a stale cached answer.
            clarify = self._build_clarify_response(question, [], company_code)
            if clarify:
                logger.info("stream:clarify_intercept | q=%r", question[:60])
                if session_id:
                    session_store.save(session_id, question, clarify)
                yield {"token": clarify}
                yield {"done": True, "sources": []}
                return

            # ── Heartbeat #1 — before query-rewrite LLM call (can be slow) ──
            yield {"status": "thinking"}
            retrieval_q = await self._build_retrieval_query(question, history)

            # ── Answer cache — use original question to avoid history bleed ─
            if not force_rag:
                yield {"status": "thinking"}
                cached = await retrieval_service.match_answer_cache(question, company_code)
                if cached:
                    if session_id:
                        session_store.save(session_id, question, cached["answer"])
                    yield {"token": cached["answer"]}
                    yield {"done": True, "sources": []}
                    return

                # ── Canonical Q&A — use original question ─────────────────
                yield {"status": "thinking"}
                qa = await retrieval_service.match_canonical_qa(question, company_code)
                if qa:
                    if session_id:
                        session_store.save(session_id, question, qa["answer"])
                    yield {"token": qa["answer"]}
                    yield {"done": True, "sources": []}
                    return

            # ── RAG — retrieval_q (enriched) for embedding, original for LLM
            yield {"status": "thinking"}
            context_rows = await retrieval_service.search_context(retrieval_q, company_code)

            context = self._build_context(context_rows)

            full_answer = ""
            async for token in self._generate_answer_stream(self._coerce_to_question(question), context, history):
                full_answer += token
                yield {"token": token}

        except Exception as exc:
            logger.error("stream:pipeline_error | %s: %s", type(exc).__name__, exc, exc_info=True)
            err = f"ขออภัยครับ ระบบขัดข้องชั่วคราว ({type(exc).__name__}: {exc})"
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

        no_answer = self._is_no_answer(full_answer, context_rows, company_code)
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
        """Build prompt, call the LLM (non-streaming), and yield the full answer.

        We deliberately use the non-streaming chat() call here even though this
        is an async generator.  The cloud model (gpt-oss:20b-cloud) ignores the
        CONTEXT when called with stream=True, consistently returning
        "ขณะนี้ยังไม่มีข้อมูลส่วนนี้ครับ" for valid RAG queries.  Using
        stream=False (non-streaming) produces correct answers.  The SSE
        connection is maintained by the heartbeat {"status": "thinking"} events
        emitted by answer_stream(); the final answer arrives as one token.
        """
        logger.debug(
            "stream:llm_call | q=%r | ctx_len=%d | hist_turns=%d",
            question[:60], len(context), len(history),
        )
        answer = await self._generate_answer(question, context, history)
        yield answer

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

        current_prompt = f"""[คำสั่งระบบ — ห้ามถามกลับ ตอบจาก CONTEXT เท่านั้น]

ระบบได้ตรวจสอบความชัดเจนของคำถามก่อนส่งมาให้คุณแล้ว งานของคุณคือ **ตอบจาก CONTEXT เท่านั้น** ห้ามถามกลับผู้ใช้ไม่ว่ากรณีใด

━━━ กฎการตอบ ━━━
  CONTEXT มีข้อมูลตรงกัน → ตอบตามกฎด้านล่าง
  CONTEXT ไม่มีข้อมูล    → ตอบว่า "ขณะนี้ยังไม่มีข้อมูลส่วนนี้ครับ" แล้วหยุด

1. ห้ามใช้ความรู้ทั่วไปหรือข้อมูลภายนอก CONTEXT เด็ดขาด
2. ถามว่า "มีไหม / มีหรือเปล่า" → ขึ้นต้นด้วย "มีครับ" หรือ "ไม่มีครับ"
3. ถามว่า "ได้ไหม / ทำได้ไหม" → ขึ้นต้นด้วย "ได้ครับ" หรือ "ไม่ได้ครับ"
4. ถามว่า "ใช่ไหม / จริงไหม" → ขึ้นต้นด้วย "ใช่ครับ" หรือ "ไม่ใช่ครับ"
5. อย่าใช้ประโยค "ไม่พบข้อมูลในฐานความรู้"
6. ถ้าคำถามอ้างอิงบทสนทนาก่อนหน้า ให้ใช้ประวัติด้านบนประกอบการตอบ
7. ถ้ามีขั้นตอน ให้เรียงเป็นข้อ ตอบสั้น กระชับ ภาษาสุภาพ เป็นกันเอง
8. ถ้า QUESTION เป็นชื่อหัวข้อ/ประเภทสินค้าหรือระบุหัวข้อเฉพาะ (เช่น "ประกันรถยนต์" "ที่อยู่สาขา" "เบอร์กรมธรรม์") และ CONTEXT มีข้อมูล → สรุปข้อมูลสำคัญจาก CONTEXT เลย
9. ห้ามถามผู้ใช้ว่า "หมายถึงอะไร" หรือ "ขอรายละเอียดเพิ่มเติม" — งานคือตอบจาก CONTEXT เท่านั้น
10. ถ้าถามว่า "มีกี่..." หรือ "มีอะไรบ้าง" → ระบุเฉพาะรายการที่ปรากฏใน CONTEXT เท่านั้น ห้ามนับหรือสรุปจำนวนเองถ้า CONTEXT ไม่ได้ระบุตัวเลขไว้ชัดเจน
11. ประโยคแรกต้องตอบตรงคำถามที่ถามเสมอ เช่น "บริษัทก่อตั้งปี 2490 ครับ" หรือ "ทุนจดทะเบียน 500 ล้านบาทครับ" จากนั้นจึงขยายรายละเอียด
12. ตอบเฉพาะสิ่งที่คำถามถามเท่านั้น ห้ามเพิ่มหัวข้ออื่นที่ไม่เกี่ยวข้องกับคำถาม
13. คำตอบต้องตรงกับ "ประเภท" ของคำถาม แม้ CONTEXT จะมีข้อมูลอื่นปนอยู่ก็ห้ามเอามาตอบแทน:
    - ถาม "ที่ไหน / อยู่ที่ไหน / ที่อยู่" → ตอบ **สถานที่/ที่อยู่** เท่านั้น (ห้ามตอบทุนจดทะเบียน ปีก่อตั้ง หรือข้อมูลบริษัทอื่น)
    - ถาม "เมื่อไหร่ / ปีไหน" → ตอบ **วัน/เวลา/ปี**
    - ถาม "เท่าไหร่ / กี่บาท" → ตอบ **จำนวน/ตัวเลข**
    - ถาม "เบอร์ / โทร" → ตอบ **เบอร์โทรศัพท์**
    ถ้า CONTEXT ไม่มีข้อมูลที่ตรงประเภทคำถาม → ตอบ "ขณะนี้ยังไม่มีข้อมูลส่วนนี้ครับ"

CONTEXT:
{context}

QUESTION: {question}"""

        # Build message list: system → history turns → current question
        messages: list[dict] = [{"role": "system", "content": system_msg}]
        messages.extend(history)   # previous user/assistant turns
        messages.append({"role": "user", "content": current_prompt})

        # Answer generation backend is configurable (see ANSWER_LLM_USE_LOCAL):
        #   - cloud chat_llm + OLLAMA_CHAT_MODEL    → fast, default
        #   - local_llm (llm-server) + ANSWER_LLM_MODEL → slower but follows
        #     question-type rules more reliably (e.g. address vs capital).
        if settings.ANSWER_LLM_USE_LOCAL:
            return await local_llm.chat(messages, model=settings.ANSWER_LLM_MODEL)
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

        # Never cache "no answer" or clarifying-question responses.
        # Caching them causes the bot to serve stale "ไม่มีข้อมูล" indefinitely
        # even after relevant data is added to the knowledge base.
        no_answer_phrases = bot_settings_service.get(company_code, "no_answer_phrases")
        clarify_phrases   = bot_settings_service.get(company_code, "clarify_phrases")
        skip_phrases = list(no_answer_phrases) + list(clarify_phrases)
        if any(phrase in answer for phrase in skip_phrases):
            logger.debug("answer_cache_skip | bad_answer phrase | q=%r", question[:60])
            return
        if not rows:
            logger.debug("answer_cache_skip | no context rows | q=%r", question[:60])
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
