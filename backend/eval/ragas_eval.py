#!/usr/bin/env python
"""
Ragas evaluation script for Enterprise LLM Wiki RAG pipeline.

Measures RAG quality using our own Ollama LLM as the judge — no OpenAI needed.

── Setup ─────────────────────────────────────────────────────────────────────
    cd backend
    pip install -r eval/requirements.txt

── Run ───────────────────────────────────────────────────────────────────────
    python -m eval.ragas_eval                    # all questions, company=DEVES
    python -m eval.ragas_eval --company DEVES    # explicit company
    python -m eval.ragas_eval --limit 3          # quick smoke-test (3 questions)

── Metrics ───────────────────────────────────────────────────────────────────
Always (reference-free — no ground_truth needed):
  • Faithfulness             : Are LLM claims grounded in retrieved context?
  • Answer Relevancy         : Does the answer actually address the question?
  • Context Precision        : Are retrieved chunks relevant to the question?

When ground_truth is present in dataset.json:
  • Context Recall           : Does the context cover the ground truth?
  • Answer Correctness       : Is the answer factually correct?

── Output ────────────────────────────────────────────────────────────────────
Results are printed as a table and saved to eval/results/eval_<company>_<ts>.json
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# ── Add backend root to Python path ──────────────────────────────────────────
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

# ── Now import backend modules ────────────────────────────────────────────────
from app.core.config import settings                          # noqa: E402
from app.db.supabase_client import supabase                   # noqa: E402
from app.services.retrieval_service import retrieval_service  # noqa: E402
from app.services.chat_service import chat_service            # noqa: E402
from app.services.ollama_client import OllamaClient           # noqa: E402


def patch_llm(base_url: str, model: str) -> None:
    """Redirect chat_llm to a different Ollama server (e.g. local) at runtime."""
    import app.services.ollama_client as oc
    import app.services.chat_service as cs
    new_client = OllamaClient(base_url)
    oc.chat_llm  = new_client
    cs.chat_llm  = new_client
    # Update the model in settings object (in-memory only)
    settings.__dict__["OLLAMA_CHAT_MODEL"] = model
    settings.__dict__["OLLAMA_BASE_URL"]   = base_url
    print(f"  LLM patched → {base_url}  model={model}")


# ── Step 1: collect RAG outputs for every question ────────────────────────────

async def _run_one(question: str, company_code: str) -> dict | None:
    """Run the production pipeline for one question and return (answer, contexts).

    Mirrors chat_service.answer():
      1. Canonical QA lookup — use exact answer if found (no hallucination risk)
      2. RAG retrieval — always run so Ragas gets real context chunks to evaluate
    """
    try:
        # ── Contexts: real RAG retrieval (for Ragas context metrics) ─────────
        rows = await retrieval_service.search_context(question, company_code)
        contexts: list[str] = [
            r.get("content_markdown") or r.get("content") or r.get("answer") or ""
            for r in rows
        ]
        contexts = [c.strip() for c in contexts if c.strip()]

        # ── Answer: the EXACT production path (answer cache → canonical QA →
        # clarify → RAG → generate). Evaluating this means the scores reflect
        # what a real user actually receives, not a simplified RAG-only path.
        result = await chat_service.answer(
            question=question,
            company_code=company_code,
            force_rag=False,
            session_id=f"eval_{abs(hash(question)) % 100000}",
            track_unanswered=False,
        )
        answer = result.answer if hasattr(result, "answer") else str(result)
        return {"contexts": contexts, "answer": answer}
    except Exception as exc:
        import traceback
        print(f"    ✗ {type(exc).__name__}: {exc or '(no message)'}")
        print(f"    {traceback.format_exc().splitlines()[-1]}")
        return None


async def collect_samples(items: list[dict], company_code: str) -> list[dict]:
    """Run the RAG pipeline for every item and return Ragas-ready samples."""
    samples = []
    for i, item in enumerate(items, 1):
        q = item["question"]
        print(f"[{i}/{len(items)}] {q[:70]}")
        result = await _run_one(q, company_code)
        # Retry once on failure (first run may hit cold-start issues)
        if result is None:
            print(f"    ↻ retrying...")
            result = await _run_one(q, company_code)
        if result is None:
            continue

        sample: dict = {
            "user_input":         q,
            "response":           result["answer"],
            "retrieved_contexts": result["contexts"],
        }
        if "ground_truth" in item:
            sample["reference"] = item["ground_truth"]

        print(
            f"    ✓ contexts={len(result['contexts'])}  "
            f"answer={result['answer'][:60].strip()!r}"
        )
        samples.append(sample)

    return samples


# ── Step 2: build Ragas dataset ───────────────────────────────────────────────

def build_dataset(samples: list[dict]):
    from ragas import EvaluationDataset
    from ragas.dataset_schema import SingleTurnSample

    return EvaluationDataset(
        samples=[SingleTurnSample(**s) for s in samples]
    )


# ── Step 3: configure metrics with our own Ollama LLM ────────────────────────

def build_metrics(samples: list[dict], judge_base_url: str | None = None,
                  judge_model: str | None = None, judge_key: str | None = None):
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)

    from ragas.metrics import faithfulness, answer_relevancy, context_precision
    from ragas.llms import LangchainLLMWrapper
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from langchain_openai import ChatOpenAI
    from langchain_community.embeddings import OllamaEmbeddings

    # An OpenAI-compatible judge. By default the local/cloud Ollama; override with
    # --judge-base-url/--judge-model/--judge-key to use a fast, reliable provider
    # (e.g. cerebras gpt-oss-120b) so the LLM-judge metrics don't time out.
    judge_base  = judge_base_url or settings.OLLAMA_BASE_URL
    base_v1     = judge_base if judge_base.rstrip("/").endswith("/v1") else f"{judge_base.rstrip('/')}/v1"
    judge_mdl   = judge_model or settings.OLLAMA_CHAT_MODEL
    judge_api   = judge_key or (settings.OLLAMA_API_KEY or "ollama")
    print(f"  Judge → {base_v1}  model={judge_mdl}")

    # gpt-oss reasoning models can spend the whole budget "thinking" and time
    # out on judge prompts — force low reasoning effort to keep them snappy.
    extra_body = {"reasoning_effort": "low"} if "gpt-oss" in judge_mdl.lower() else {}
    chat_lc = ChatOpenAI(
        base_url=base_v1,
        api_key=judge_api,
        model=judge_mdl,
        temperature=0,
        timeout=90,
        max_retries=4,
        extra_body=extra_body,
    )
    # Local Ollama for embeddings (Answer Relevancy uses cosine similarity)
    embed_lc = OllamaEmbeddings(
        base_url=settings.OLLAMA_EMBED_BASE_URL,
        model=settings.OLLAMA_EMBED_MODEL,
    )

    llm = LangchainLLMWrapper(chat_lc)
    emb = LangchainEmbeddingsWrapper(embed_lc)

    faithfulness.llm        = llm
    answer_relevancy.llm        = llm
    answer_relevancy.embeddings = emb
    context_precision.llm   = llm

    # answer_relevancy generates `strictness` questions in ONE call via the
    # OpenAI `n` param. Many providers (cerebras, sambanova, …) reject n>1, so
    # force n=1 — slightly noisier relevancy but compatible with every provider.
    if hasattr(answer_relevancy, "strictness"):
        answer_relevancy.strictness = 1

    metrics = [faithfulness, answer_relevancy, context_precision]

    # Only enable ground-truth metrics when EVERY sample has a reference.
    # Partial reference sets cause KeyError in context_recall / answer_correctness.
    all_have_reference = len(samples) > 0 and all("reference" in s for s in samples)
    if all_have_reference:
        from ragas.metrics import context_recall, answer_correctness
        context_recall.llm              = llm
        answer_correctness.llm          = llm
        answer_correctness.embeddings   = emb   # use local Ollama — no OpenAI key needed
        answer_correctness.weights      = [0.4, 0.6]   # factuality weighted higher
        metrics += [context_recall, answer_correctness]
        print("ℹ  Ground truth found → running 5 metrics\n")
    else:
        has_any = any("reference" in s for s in samples)
        if has_any:
            print("ℹ  Partial ground truth — running 3 reference-free metrics only\n"
                  "   (add ground_truth to ALL questions to enable Context Recall + Answer Correctness)\n")
        else:
            print("ℹ  No ground truth   → running 3 reference-free metrics\n")

    return metrics


# ── Step 4: print + save results ──────────────────────────────────────────────

def _aggregate(df) -> dict[str, float | None]:
    """Compute mean per metric column; returns None (→ JSON null) when all values are NaN."""
    NON_METRIC = {"user_input", "response", "retrieved_contexts", "reference"}
    result = {}
    for col in df.columns:
        if col in NON_METRIC or df[col].dtype not in ("float64", "float32"):
            continue
        val = df[col].dropna().mean()
        # NaN means all jobs failed — store as None so JSON writes null
        result[col] = None if (val != val) else round(float(val), 4)
    return result


def print_results(result, samples: list[dict]) -> None:
    df        = result.to_pandas()
    aggregate = _aggregate(df)

    print(f"\n{'─'*62}")
    print("  Aggregate scores")
    print(f"{'─'*62}")
    for metric_name, score in aggregate.items():
        if score is None or (isinstance(score, float) and score != score):
            print(f"  {metric_name:<40}  n/a   (all jobs timed out)")
            continue
        bar_len = max(0, min(20, int(score * 20)))
        bar = "█" * bar_len + "░" * (20 - bar_len)
        print(f"  {metric_name:<40} {score:.4f}  {bar}")
    print(f"{'─'*62}\n")

    print("  Per-question faithfulness (top concern):")
    if "faithfulness" in df.columns:
        for _, row in df.iterrows():
            q   = str(row.get("user_input", ""))[:55]
            val = row.get("faithfulness")
            flag = "⚠" if isinstance(val, float) and val == val and val < 0.7 else " "
            print(f"  {flag} {q:<55} {val:.2f}" if isinstance(val, float) and val == val else f"    {q}")


def save_results(result, samples: list[dict], company_code: str) -> Path:
    df          = result.to_pandas()
    aggregate   = _aggregate(df)
    metric_cols = list(aggregate.keys())

    # Merge per-question metric scores into each sample
    scored_samples = []
    for i, sample in enumerate(samples):
        scored = dict(sample)
        if i < len(df):
            for col in metric_cols:
                val = df.iloc[i].get(col)
                if val is not None and val == val:   # skip NaN
                    scored[col] = round(float(val), 4)
        scored_samples.append(scored)

    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = results_dir / f"eval_{company_code}_{ts}.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "company":   company_code,
                "timestamp": ts,
                "n_samples": len(samples),
                "metrics":   metric_cols,
                "aggregate": aggregate,
                "samples":   scored_samples,
            },
            f,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,   # never emit bare NaN — JS JSON.parse rejects it
        )
    return out_path


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ragas evaluation for Enterprise LLM Wiki"
    )
    parser.add_argument("--company", default="DEVES",
                        help="Company code to evaluate (default: DEVES)")
    parser.add_argument("--limit",   type=int, default=None,
                        help="Limit number of questions (useful for quick tests)")
    parser.add_argument("--llm-base-url", default=None,
                        help="Override the ANSWER-generation LLM base URL, e.g. http://localhost:11434")
    parser.add_argument("--llm-model", default=None,
                        help="Override the ANSWER-generation LLM model name")
    parser.add_argument("--judge-base-url", default=None,
                        help="Override the Ragas JUDGE base URL, e.g. https://api.cerebras.ai/v1")
    parser.add_argument("--judge-model", default=None,
                        help="Override the Ragas JUDGE model, e.g. gpt-oss-120b")
    parser.add_argument("--judge-key", default=None,
                        help="API key for the JUDGE provider (needed for cloud judges)")
    parser.add_argument("--judge-provider", default=None,
                        help="Use a provider from the DB as judge by name (e.g. cerebras); "
                             "pulls base_url+key automatically. Combine with --judge-model.")
    parser.add_argument("--max-workers", type=int, default=2,
                        help="Parallel judge calls. Use 1 for rate-limited cloud judges.")
    args = parser.parse_args()

    # Resolve --judge-provider (DB lookup) into base_url/key
    if args.judge_provider:
        row = (supabase.table("ai_providers").select("*")
               .eq("name", args.judge_provider).single().execute().data)
        if not row:
            print(f"Judge provider '{args.judge_provider}' not found in ai_providers.")
            sys.exit(1)
        args.judge_base_url = args.judge_base_url or row["base_url"]
        args.judge_key      = args.judge_key or row["api_key"]

    # Patch LLM if local override requested
    if args.llm_base_url or args.llm_model:
        patch_llm(
            args.llm_base_url or settings.OLLAMA_BASE_URL,
            args.llm_model    or settings.OLLAMA_CHAT_MODEL,
        )

    # Load dataset
    dataset_path = Path(__file__).parent / "dataset.json"
    with open(dataset_path, encoding="utf-8") as f:
        items: list[dict] = json.load(f)

    if args.limit:
        items = items[: args.limit]

    print(f"\n{'='*62}")
    print(f"  Ragas Evaluation")
    print(f"  Company : {args.company}")
    print(f"  Model   : {args.llm_model or settings.OLLAMA_CHAT_MODEL}")
    print(f"  Questions: {len(items)}")
    print(f"{'='*62}\n")

    # ── Collect RAG outputs ───────────────────────────────────────────────────
    samples = asyncio.run(collect_samples(items, args.company))

    if not samples:
        print("No samples collected — check backend config and Ollama connectivity.")
        sys.exit(1)

    print(f"\nCollected {len(samples)}/{len(items)} samples.")
    print("Running Ragas evaluation (each metric calls LLM as judge)...\n")

    # ── Evaluate ──────────────────────────────────────────────────────────────
    from ragas import evaluate, RunConfig

    dataset    = build_dataset(samples)
    metrics    = build_metrics(
        samples,
        judge_base_url=args.judge_base_url,
        judge_model=args.judge_model,
        judge_key=args.judge_key,
    )
    run_config = RunConfig(
        max_workers=args.max_workers,  # 1 = sequential → avoids cloud 429 bursts
        timeout=120,                   # seconds per job
        max_retries=3,
    )
    result = evaluate(dataset=dataset, metrics=metrics, run_config=run_config)

    # ── Output — save first, then print (crash in print won't lose data) ──────
    out_path = save_results(result, samples, args.company)
    print(f"Results saved → {out_path}\n")
    print_results(result, samples)


if __name__ == "__main__":
    main()
