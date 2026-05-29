"""
Public (no-auth) endpoints for the Floating Chat widget.

/api/public/companies  — list active companies
/api/public/chat       — same RAG pipeline as /api/chat, no auth required

Whitelisted in ApiKeyMiddleware via _PUBLIC_PREFIXES.
"""

import json
import time

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.db.supabase_client import supabase
from app.services.chat_service import chat_service

router = APIRouter(prefix="/api/public", tags=["public"])


# ── Companies (with TTL cache) ────────────────────────────────────────────────

_companies_cache: list | None = None
_companies_cache_ts: float = 0.0
_COMPANIES_TTL = 300  # 5 minutes — companies rarely change


@router.get("/companies")
def list_public_companies():
    """Return active companies for the floating-chat company selector.

    Results are cached in memory for 5 minutes so that repeated widget
    mounts (and page refreshes) don't hammer Supabase on every request.
    """
    global _companies_cache, _companies_cache_ts

    now = time.monotonic()
    if _companies_cache is not None and (now - _companies_cache_ts) < _COMPANIES_TTL:
        return _companies_cache

    res = (
        supabase.table("companies")
        .select("company_code, company_name")
        .eq("is_active", True)
        .order("company_code")
        .execute()
    )
    _companies_cache = [
        {"code": row["company_code"], "name": row["company_name"]}
        for row in (res.data or [])
    ]
    _companies_cache_ts = now
    return _companies_cache


# ── Chat ──────────────────────────────────────────────────────────────────────

class PublicChatRequest(BaseModel):
    message:      str
    company_code: str = "DEVES"
    session_id:   str | None = None


@router.post("/chat")
async def public_chat(req: PublicChatRequest):
    """
    Public chat — no API key required.
    Uses the exact same RAG pipeline as the authenticated /api/chat endpoint
    (answer cache → canonical QA → RAG), with session memory support.
    """
    result = await chat_service.answer(
        question=req.message,
        company_code=req.company_code,
        force_rag=False,
        session_id=req.session_id,
        track_unanswered=True,
    )

    # Normalise to { answer, sources } for the FloatingChat widget
    sources = [
        {"title": r.label, "url": r.url}
        for r in (result.source_refs or [])
    ]

    return {"answer": result.answer, "sources": sources}


# ── Streaming Chat ─────────────────────────────────────────────────────────────

@router.post("/chat/stream")
async def public_chat_stream(req: PublicChatRequest):
    """
    Streaming version of public chat — returns Server-Sent Events.

    Each event is a JSON object:
      {"token": "<text>"}            — one LLM token chunk
      {"done": true, "sources": []}  — final event with source refs
    """
    async def event_generator():
        try:
            async for chunk in chat_service.answer_stream(
                question=req.message,
                company_code=req.company_code,
                force_rag=False,
                session_id=req.session_id,
                track_unanswered=True,
            ):
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        except Exception as exc:
            error = {"done": True, "error": str(exc), "sources": []}
            yield f"data: {json.dumps(error)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
