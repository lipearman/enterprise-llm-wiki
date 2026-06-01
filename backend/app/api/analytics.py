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

from fastapi import APIRouter, Query, Request

from app.db.supabase_client import supabase
from app.core.config import settings
from app.services.audit_service import audit_log

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


@router.get("/agent-graph")
def agent_graph():
    """Phase 7 — introspect the LangGraph agentic StateGraph for visualization.
    Returns nodes + edges (with conditional flag) + a Mermaid diagram source."""
    try:
        from app.services.agent_graph import build_agent_graph
        from app.services.chat_service import chat_service
        g = build_agent_graph(chat_service).get_graph()
        nodes = list(g.nodes.keys())
        edges = [{"source": e.source, "target": e.target,
                  "conditional": bool(getattr(e, "conditional", False))} for e in g.edges]
        try:
            mermaid = g.draw_mermaid()
        except Exception:
            mermaid = None
        return {"enabled": settings.ENABLE_LANGGRAPH, "available": True,
                "nodes": nodes, "edges": edges, "mermaid": mermaid}
    except Exception as exc:
        logger.warning("agent_graph_introspect_failed | %s", str(exc)[:100])
        return {"enabled": settings.ENABLE_LANGGRAPH, "available": False,
                "error": str(exc)[:120], "nodes": [], "edges": []}


@router.get("/agent-runs")
def agent_runs(limit: int = Query(25, ge=1, le=200), company_code: str | None = Query(None),
               search: str | None = Query(None)):
    """Phase 7 — recent agentic runs with the node-by-node step trace, for the
    observability view. Persisted in agent_runs (in-memory fallback). Supports
    ``search`` (question contains)."""
    try:
        from app.services.agent_graph import get_recent_runs, get_run_stats
        return {"enabled": settings.ENABLE_LANGGRAPH,
                "stats": get_run_stats(company_code),
                "runs": get_recent_runs(limit, company_code, search)}
    except Exception as exc:
        logger.warning("agent_runs_failed | %s", str(exc)[:100])
        return {"enabled": settings.ENABLE_LANGGRAPH, "runs": [], "stats": {}, "error": str(exc)[:120]}


@router.delete("/agent-runs")
def purge_agent_runs(request: Request, older_than_days: int = Query(30, ge=0, le=3650)):
    """Retention — delete agent runs older than ``older_than_days``."""
    from app.services.agent_graph import purge_old_runs
    removed = purge_old_runs(older_than_days)
    audit_log("analytics.purge_runs", request=request, detail={"older_than_days": older_than_days, "removed": removed})
    return {"ok": True, "removed": removed, "older_than_days": older_than_days}


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
