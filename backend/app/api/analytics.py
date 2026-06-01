"""
Analytics / overview endpoints (admin — requires API key). Phase 6.

GET /api/analytics/overview?company_code=DEVES
    → aggregated stats for the admin dashboard: content counts, chat activity,
      provider config, recent audit, latest eval scores. Each section is
      independent — a failure in one returns null for that section, not a 500.
"""

import glob
import json
import logging
import os

from fastapi import APIRouter, Query

from app.db.supabase_client import supabase
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _count(table: str, company_code: str | None = None, **filters) -> int | None:
    try:
        q = supabase.table(table).select("id", count="exact")
        if company_code:
            q = q.eq("company_code", company_code)
        for k, v in filters.items():
            q = q.eq(k, v)
        return q.execute().count
    except Exception as exc:
        logger.warning("analytics_count_failed | %s | %s", table, str(exc)[:80])
        return None


def _content_stats(cc: str) -> dict:
    return {
        "wiki_pages":      _count("wiki_pages", cc),
        "canonical_qa":    _count("canonical_qa", cc),
        "document_chunks": _count("document_chunks", cc),
        "sources":         _count("knowledge_sources", cc),
    }


def _chat_stats(cc: str) -> dict:
    total = _count("unanswered_questions", cc)
    out = {"unanswered_total": total, "recent_unanswered": []}
    try:
        rows = (supabase.table("unanswered_questions")
                .select("question,created_at,resolved")
                .eq("company_code", cc).order("created_at", desc=True).limit(5).execute().data or [])
        out["recent_unanswered"] = [{"question": r.get("question"), "resolved": r.get("resolved")} for r in rows]
    except Exception:
        pass
    return out


def _provider_stats() -> dict:
    try:
        provs = supabase.table("ai_providers").select("id,name,is_active").execute().data or []
        assigns = supabase.table("ai_role_assignments").select("role,provider_id,is_active").execute().data or []
        by_role: dict[str, int] = {}
        for a in assigns:
            if a.get("is_active"):
                by_role[a["role"]] = by_role.get(a["role"], 0) + 1
        return {
            "total": len(provs),
            "active": sum(1 for p in provs if p.get("is_active")),
            "roles_configured": by_role,
        }
    except Exception as exc:
        logger.warning("analytics_providers_failed | %s", str(exc)[:80])
        return None


def _audit_stats(cc: str) -> dict:
    try:
        rows = (supabase.table("audit_logs")
                .select("action,status,created_at")
                .order("created_at", desc=True).limit(8).execute().data or [])
        return {"recent": [{"action": r.get("action"), "status": r.get("status"),
                            "at": r.get("created_at")} for r in rows]}
    except Exception:
        return None


def _latest_eval() -> dict | None:
    """Read the newest eval/results/eval_*.json (RAG quality scores)."""
    try:
        base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "eval", "results")
        files = sorted(glob.glob(os.path.join(base, "eval_*.json")), reverse=True)
        if not files:
            return None
        with open(files[0], encoding="utf-8") as f:
            d = json.load(f)
        return {
            "timestamp": d.get("timestamp"),
            "company": d.get("company"),
            "n_samples": d.get("n_samples"),
            "aggregate": d.get("aggregate", {}),
        }
    except Exception as exc:
        logger.warning("analytics_eval_failed | %s", str(exc)[:80])
        return None


@router.get("/overview")
def overview(company_code: str | None = Query(None)):
    cc = company_code or settings.DEFAULT_COMPANY_CODE
    return {
        "company_code": cc,
        "content":   _content_stats(cc),
        "chat":      _chat_stats(cc),
        "providers": _provider_stats(),
        "audit":     _audit_stats(cc),
        "eval":      _latest_eval(),
        "agentic": {
            "enabled":      settings.ENABLE_AGENTIC_ANSWER,
            "planner":      settings.ENABLE_QUERY_PLANNER,
            "llm_rerank":   settings.ENABLE_LLM_RERANK,
            "graph_hops":   settings.GRAPHRAG_MAX_HOPS,
        },
    }
