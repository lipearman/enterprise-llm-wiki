"""
LangGraph agentic RAG graph (Phase 6.3).

Re-expresses the agentic loop (retrieve → generate → validate → reformulate) as
an explicit LangGraph StateGraph. Its value over the imperative loop is
**streaming the intermediate steps** to the UI (so the user sees "🔍 searching…
→ 🔎 validating… → ✍️ answering…") plus easier visualisation/extension.

chat_service is injected (``svc``) so the node functions reuse the existing
retrieval / generation / validation logic without a circular import.
"""

import logging
from typing import TypedDict

from app.core.config import settings
from app.services.retrieval_service import retrieval_service

logger = logging.getLogger(__name__)

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
    try:
        graph = build_agent_graph(svc)
        async for event in graph.astream(init, stream_mode="updates"):
            for node, update in event.items():
                if isinstance(update, dict):
                    state.update(update)
                label = _NODE_LABELS.get(node)
                if label:
                    yield {"status": node, "label": label}
    except Exception as exc:
        logger.warning("agent_graph_stream | fallback to single-pass | %s", str(exc)[:120])
        rows = await retrieval_service.search_context(retrieval_q, company_code)
        ctx = svc._build_context(rows)
        ans = await svc._generate_answer(svc._coerce_to_question(question), ctx, history)
        state = {"answer": ans, "context_rows": rows}
    yield {"answer": state.get("answer", ""), "context_rows": state.get("context_rows", [])}
