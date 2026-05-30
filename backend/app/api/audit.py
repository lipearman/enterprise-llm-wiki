"""
Audit log endpoints (admin — requires API key).

GET  /api/audit/logs   — paginated audit log entries, newest first
GET  /api/audit/actions — distinct action names (for frontend filter dropdown)
"""

from fastapi import APIRouter, Query

from app.db.supabase_client import supabase

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("/logs")
def list_audit_logs(
    company_code: str | None = Query(None),
    action:       str | None = Query(None, description="Prefix match, e.g. 'chat' or 'source.add'"),
    status:       str | None = Query(None, description="ok | error | fail"),
    limit:  int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Return paginated audit log entries, newest first."""
    q = (
        supabase.table("audit_logs")
        .select("*", count="exact")
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
    )
    if company_code:
        q = q.eq("company_code", company_code)
    if action:
        q = q.like("action", f"{action}%")
    if status:
        q = q.eq("status", status)

    res = q.execute()
    return {"items": res.data or [], "total": res.count or 0}


@router.get("/actions")
def list_audit_actions():
    """Return the list of known action names for the filter dropdown."""
    return {
        "actions": [
            "auth.login",
            "chat.question",
            "source.add_url",
            "source.add_file",
            "source.delete",
            "source.fix_titles",
            "source.clean_content",
            "unanswered.resolve",
            "unanswered.delete",
            "job.crawl_all",
            "job.run_pending",
        ]
    }
