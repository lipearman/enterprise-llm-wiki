"""
Admin endpoints for unanswered questions captured from the FloatingChat widget.

GET  /api/unanswered             — paginated list (filter by company / resolved)
PATCH /api/unanswered/{id}/resolve — mark as resolved (with optional note)
DELETE /api/unanswered/{id}      — delete a record
"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.db.supabase_client import supabase

router = APIRouter(prefix="/api/unanswered", tags=["unanswered"])


# ── List ───────────────────────────────────────────────────────────────────────

@router.get("")
def list_unanswered(
    company_code: str | None = Query(None),
    is_resolved:  bool | None = Query(None),
    limit:  int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Return paginated unanswered questions, newest first."""
    q = (
        supabase.table("unanswered_questions")
        .select("*", count="exact")
        .order("asked_at", desc=True)
        .range(offset, offset + limit - 1)
    )
    if company_code:
        q = q.eq("company_code", company_code)
    if is_resolved is not None:
        q = q.eq("is_resolved", is_resolved)

    res = q.execute()
    return {"items": res.data or [], "total": res.count or 0}


# ── Stats ──────────────────────────────────────────────────────────────────────

@router.get("/stats")
def unanswered_stats(company_code: str | None = Query(None)):
    """Return total and unresolved counts (for badge / dashboard)."""
    q_all = supabase.table("unanswered_questions").select("id", count="exact")
    q_open = supabase.table("unanswered_questions").select("id", count="exact").eq("is_resolved", False)
    if company_code:
        q_all  = q_all.eq("company_code", company_code)
        q_open = q_open.eq("company_code", company_code)
    total    = q_all.execute().count or 0
    unresolved = q_open.execute().count or 0
    return {"total": total, "unresolved": unresolved}


# ── Resolve ────────────────────────────────────────────────────────────────────

class ResolvePayload(BaseModel):
    note: str | None = None


@router.patch("/{item_id}/resolve")
def resolve_question(item_id: str, body: ResolvePayload = ResolvePayload()):
    """Mark a question as resolved, with an optional admin note."""
    data: dict = {
        "is_resolved": True,
        "resolved_at": datetime.now(timezone.utc).isoformat(),
    }
    if body.note is not None:
        data["note"] = body.note

    res = supabase.table("unanswered_questions").update(data).eq("id", item_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Question not found")
    return {"ok": True}


# ── Delete ─────────────────────────────────────────────────────────────────────

@router.delete("/{item_id}")
def delete_question(item_id: str):
    """Delete an unanswered question record."""
    supabase.table("unanswered_questions").delete().eq("id", item_id).execute()
    return {"ok": True}
