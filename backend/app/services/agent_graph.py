"""
LangGraph agentic RAG graph (Phase 6.3).

Re-expresses the agentic loop (retrieve → generate → validate → reformulate) as
an explicit LangGraph StateGraph. Its value over the imperative loop is
**streaming the intermediate steps** to the UI (so the user sees "🔍 searching…
→ 🔎 validating… → ✍️ answering…") plus easier visualisation/extension.

chat_service is injected (``svc``) so the node functions reuse the existing
retrieval / generation / validation logic without a circular import.
"""

import asyncio
import logging
import time
from collections import deque
from datetime import datetime
from typing import TypedDict

from app.core.config import settings
from app.db.supabase_client import supabase
from app.services.retrieval_service import retrieval_service

logger = logging.getLogger(__name__)

# In-memory ring buffer — fallback when the agent_runs table isn't migrated.
_RECENT_RUNS: deque = deque(maxlen=25)


def _persist_run(run: dict) -> None:
    """Store a run in agent_runs (durable). Falls back to the in-memory ring
    buffer if the table is missing."""
    try:
        supabase.table("agent_runs").insert({
            "company_code":   run.get("company_code"),
            "question":       run.get("question"),
            "answer_preview": run.get("answer_preview"),
            "duration":       run.get("duration"),
            "iterations":     run.get("iterations"),
            "steps":          run.get("steps") or [],
        }).execute()
    except Exception:
        _RECENT_RUNS.appendleft(run)


def get_recent_runs(limit: int = 25, company_code: str | None = None,
                    search: str | None = None) -> list[dict]:
    try:
        q = (supabase.table("agent_runs").select("*")
             .order("created_at", desc=True).limit(limit))
        if company_code:
            q = q.eq("company_code", company_code)
        if search:
            q = q.ilike("question", f"%{search}%")
        rows = q.execute().data or []
        return [{
            "question":       r.get("question"),
            "company_code":   r.get("company_code"),
            "at":             (r.get("created_at") or "")[:19].replace("T", " "),
            "duration":       float(r["duration"]) if r.get("duration") is not None else None,
            "iterations":     r.get("iterations"),
            "steps":          r.get("steps") or [],
            "answer_preview": r.get("answer_preview"),
        } for r in rows]
    except Exception:
        runs = list(_RECENT_RUNS)
        if company_code:
            runs = [r for r in runs if r.get("company_code") == company_code]
        if search:
            runs = [r for r in runs if search.lower() in (r.get("question", "") or "").lower()]
        return runs[:limit]


def get_run_stats(company_code: str | None = None) -> dict:
    """Aggregate stats over the recent run window (up to 500)."""
    runs = get_recent_runs(limit=500, company_code=company_code)
    n = len(runs)
    if not n:
        return {"count": 0, "avg_duration": 0, "avg_iterations": 0, "reformulate_pct": 0}
    durs = [r["duration"] for r in runs if r.get("duration") is not None]
    iters = [r["iterations"] for r in runs if r.get("iterations") is not None]
    reformed = sum(1 for r in runs if any(s.get("node") == "reformulate" for s in (r.get("steps") or [])))
    return {
        "count":           n,
        "avg_duration":    round(sum(durs) / len(durs), 1) if durs else 0,
        "avg_iterations":  round(sum(iters) / len(iters), 2) if iters else 0,
        "reformulate_pct": round(100 * reformed / n),
    }


def purge_old_runs(days: int) -> int:
    """Delete runs older than *days*. Returns the number removed (counted first,
    since Supabase delete doesn't return the rows by default)."""
    from datetime import datetime, timezone, timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    try:
        n = (supabase.table("agent_runs").select("id", count="exact")
             .lt("created_at", cutoff).execute().count) or 0
        if n:
            supabase.table("agent_runs").delete().lt("created_at", cutoff).execute()
        return n
    except Exception:
        before = len(_RECENT_RUNS)
        keep = [r for r in _RECENT_RUNS if (r.get("at", "") or "") >= cutoff[:19]]
        _RECENT_RUNS.clear()
        _RECENT_RUNS.extend(keep)
        return before - len(_RECENT_RUNS)

# Node → human-readable status shown in the chat UI while that step runs.
_NODE_LABELS = {
    "retrieve":    "🔍 กำลังค้นหาข้อมูล...",
    "generate":    "✍️ กำลังเรียบเรียงคำตอบ...",
    "validate":    "🔎 กำลังตรวจสอบความถูกต้อง...",
    "reformulate": "🔄 ข้อมูลยังไม่ครบ — กำลังค้นเพิ่มเติม...",
}


class _AgentState(TypedDict, total=False):
    question: str
    company_code: str
    history: list
    retrieval_q: str
    context_rows: list
    answer: str
    iteration: int
    sufficient: bool
    missing: str


def build_agent_graph(svc):
    """Compile the agentic StateGraph. ``svc`` is the chat_service singleton."""
    from langgraph.graph import StateGraph, START, END

    max_iters = max(1, settings.AGENTIC_MAX_ITERS)

    async def retrieve(state: _AgentState) -> dict:
        rows = await retrieval_service.search_context(state["retrieval_q"], state["company_code"])
        return {"context_rows": rows}

    async def generate(state: _AgentState) -> dict:
        ctx = svc._build_context(state.get("context_rows", []))
        ans = await svc._generate_answer(
            svc._coerce_to_question(state["question"]), ctx, state.get("history", []),
        )
        return {"answer": ans}

    async def validate(state: _AgentState) -> dict:
        if state.get("iteration", 0) >= max_iters - 1:
            return {"sufficient": True}                       # last pass — stop looping
        ctx = svc._build_context(state.get("context_rows", []))
        v = await svc._validate_answer(state["question"], state.get("answer", ""), ctx)
        return {"sufficient": v["sufficient"], "missing": v.get("missing", "")}

    async def reformulate(state: _AgentState) -> dict:
        nq = await svc._reformulate_query(state["question"], state.get("missing", ""), state["retrieval_q"])
        return {"retrieval_q": nq, "iteration": state.get("iteration", 0) + 1}

    def route(state: _AgentState) -> str:
        if state.get("sufficient") or state.get("iteration", 0) >= max_iters:
            return "end"
        return "reformulate"

    g = StateGraph(_AgentState)
    g.add_node("retrieve", retrieve)
    g.add_node("generate", generate)
    g.add_node("validate", validate)
    g.add_node("reformulate", reformulate)
    g.add_edge(START, "retrieve")
    g.add_edge("retrieve", "generate")
    g.add_edge("generate", "validate")
    g.add_conditional_edges("validate", route, {"end": END, "reformulate": "reformulate"})
    g.add_edge("reformulate", "retrieve")
    return g.compile()


async def agent_graph_stream(svc, question: str, retrieval_q: str, company_code: str, history: list):
    """Run the agentic graph, yielding ``{"status", "label"}`` per node as it
    executes, then a final ``{"answer", "context_rows"}``. Falls back to a single
    retrieve→generate pass on any graph error."""
    init: dict = {
        "question": question, "company_code": company_code, "history": history,
        "retrieval_q": retrieval_q, "context_rows": [], "answer": "",
        "iteration": 0, "sufficient": False, "missing": "",
    }
    state: dict = dict(init)
    started = time.time()
    steps: list[dict] = []
    try:
        graph = build_agent_graph(svc)
        async for event in graph.astream(init, stream_mode="updates"):
            for node, update in event.items():
                if isinstance(update, dict):
                    state.update(update)
                label = _NODE_LABELS.get(node)
                if label:
                    steps.append({"node": node, "label": label, "t": round(time.time() - started, 2)})
                    yield {"status": node, "label": label}
    except Exception as exc:
        logger.warning("agent_graph_stream | fallback to single-pass | %s", str(exc)[:120])
        steps.append({"node": "fallback", "label": "↩ single-pass (graph error)", "t": round(time.time() - started, 2)})
        rows = await retrieval_service.search_context(retrieval_q, company_code)
        ctx = svc._build_context(rows)
        ans = await svc._generate_answer(svc._coerce_to_question(question), ctx, history)
        state = {"answer": ans, "context_rows": rows}

    # Record the run for the /analytics observability view (persist off the event
    # loop so the DB write doesn't delay the final answer event).
    run = {
        "question": (question or "")[:120],
        "company_code": company_code,
        "at": datetime.now().isoformat(timespec="seconds"),
        "duration": round(time.time() - started, 2),
        "iterations": int(state.get("iteration", 0)) + 1,
        "steps": steps,
        "answer_preview": (state.get("answer", "") or "")[:120],
    }
    try:
        await asyncio.get_event_loop().run_in_executor(None, _persist_run, run)
    except Exception:
        _RECENT_RUNS.appendleft(run)
    yield {"answer": state.get("answer", ""), "context_rows": state.get("context_rows", [])}
