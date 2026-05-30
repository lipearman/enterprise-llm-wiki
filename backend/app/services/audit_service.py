"""
Audit logging service — fire-and-forget wrapper around the audit_logs table.

Usage in any route handler (sync or async):

    from app.services.audit_service import audit_log

    # sync handler
    audit_log("source.delete", request=request, detail={"source_id": sid})

    # async handler — same call, still works (adds ~5 ms; acceptable for audit)
    audit_log("chat.question", request=request, company_code=cc, detail={...})

The function never raises — audit failures are logged at DEBUG level and ignored
so they never break the main request flow.
"""

import logging
from typing import Any

from fastapi import Request

from app.db.supabase_client import supabase

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _api_key_tag(request: Request) -> str:
    """Return masked last-4 of the API key, or 'public' if no key present."""
    auth = request.headers.get("authorization", "")
    key  = auth[7:] if auth.lower().startswith("bearer ") else \
           request.headers.get("x-api-key", "")
    if not key:
        return "public"
    return f"***{key[-4:]}" if len(key) >= 4 else "***"


# ── Main entry point ──────────────────────────────────────────────────────────

def audit_log(
    action: str,
    *,
    request:      Request | None = None,
    company_code: str | None     = None,
    status:       str            = "ok",
    status_code:  int            = 200,
    detail:       dict[str, Any] | None = None,
) -> None:
    """Insert one audit_logs row.  Best-effort — never raises."""
    try:
        row: dict[str, Any] = {
            "action":       action,
            "status":       status,
            "status_code":  status_code,
            "company_code": company_code,
            "detail":       detail or {},
        }
        if request is not None:
            row["client_ip"]   = _client_ip(request)
            row["api_key_tag"] = _api_key_tag(request)
            row["http_method"] = request.method
            row["path"]        = request.url.path

        supabase.table("audit_logs").insert(row).execute()
    except Exception as exc:
        logger.debug("audit_log insert skipped: %s", exc)
