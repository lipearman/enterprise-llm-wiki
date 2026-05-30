"use client";

import { useState, useCallback, useRef } from "react";
import {
  FlaskConical, Upload, ChevronDown, ChevronUp,
  GitCompare, X, FileJson, AlertCircle, BookOpen,
} from "lucide-react";

// ── Types ─────────────────────────────────────────────────────────────────────
interface EvalSample {
  user_input:         string;
  response:           string;
  retrieved_contexts: string[];
  reference?:         string;
  [metric: string]:   unknown;   // per-question metric scores
}

interface EvalResult {
  company:   string;
  timestamp: string;
  n_samples: number;
  metrics:   string[];
  aggregate: Record<string, number | null>;
  samples:   EvalSample[];
}

// ── Constants ─────────────────────────────────────────────────────────────────
const METRIC_LABELS: Record<string, string> = {
  faithfulness:                              "Faithfulness",
  answer_relevancy:                          "Answer Relevancy",
  llm_context_precision_without_reference:   "Context Precision",
  context_recall:                            "Context Recall",
  answer_correctness:                        "Answer Correctness",
};

function metricLabel(key: string): string {
  return METRIC_LABELS[key] ?? key.replace(/_/g, " ");
}

function scoreColor(score: number): string {
  if (score >= 0.8) return "emerald";
  if (score >= 0.6) return "amber";
  return "red";
}

function scoreBg(score: number): string {
  const c = scoreColor(score);
  return c === "emerald"
    ? "bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400"
    : c === "amber"
    ? "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400"
    : "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400";
}

function barColor(score: number): string {
  const c = scoreColor(score);
  return c === "emerald" ? "bg-emerald-500" : c === "amber" ? "bg-amber-500" : "bg-red-500";
}

// ── Score bar ─────────────────────────────────────────────────────────────────
function ScoreBar({ label, score }: { label: string; score: number | null }) {
  if (score == null)
    return (
      <div className="flex items-center gap-3">
        <span className="w-44 text-sm text-slate-700 dark:text-slate-300 shrink-0 truncate">{label}</span>
        <span className="flex-1 text-xs text-slate-400 dark:text-slate-500 italic">n/a (judge timed out)</span>
      </div>
    );
  return (
    <div className="flex items-center gap-3">
      <span className="w-44 text-sm text-slate-700 dark:text-slate-300 shrink-0 truncate">
        {label}
      </span>
      <div className="flex-1 h-3 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${barColor(score)}`}
          style={{ width: `${score * 100}%` }}
        />
      </div>
      <span className={`w-14 text-right text-sm font-mono font-bold ${
        score >= 0.8 ? "text-emerald-600 dark:text-emerald-400"
          : score >= 0.6 ? "text-amber-600 dark:text-amber-400"
          : "text-red-600 dark:text-red-400"
      }`}>
        {score.toFixed(3)}
      </span>
    </div>
  );
}

// ── Score badge (table cell) ──────────────────────────────────────────────────
function ScoreBadge({ score }: { score: number | null | undefined }) {
  if (score == null || (typeof score === "number" && Number.isNaN(score)))
    return <span className="text-slate-400 text-xs">—</span>;
  return (
    <span className={`inline-block px-2 py-0.5 rounded-md text-xs font-mono font-semibold ${scoreBg(score)}`}>
      {score.toFixed(2)}
    </span>
  );
}

// ── Expandable question row ───────────────────────────────────────────────────
function QuestionRow({ sample, metrics, idx }: { sample: EvalSample; metrics: string[]; idx: number }) {
  const [open, setOpen] = useState(false);
  const scores = metrics.map((m) => sample[m] as number | undefined);
  const avgScore = scores.filter((s) => s != null).reduce((a, b) => a + (b ?? 0), 0) / (scores.filter((s) => s != null).length || 1);

  return (
    <>
      <tr
        className="hover:bg-slate-50 dark:hover:bg-slate-800/40 cursor-pointer transition-colors"
        onClick={() => setOpen(!open)}
      >
        <td className="px-4 py-3 text-xs text-slate-400 dark:text-slate-600 w-8">{idx + 1}</td>
        <td className="px-4 py-3 text-sm text-slate-800 dark:text-slate-200 max-w-xs">
          <div className="flex items-start gap-2">
            {open ? <ChevronUp size={13} className="mt-0.5 shrink-0 text-indigo-500" />
                  : <ChevronDown size={13} className="mt-0.5 shrink-0 text-slate-400" />}
            <span className="line-clamp-2">{sample.user_input}</span>
          </div>
        </td>
        {scores.map((s, i) => (
          <td key={i} className="px-4 py-3 text-center">
            <ScoreBadge score={s} />
          </td>
        ))}
        <td className="px-4 py-3 text-center">
          <ScoreBadge score={avgScore} />
        </td>
      </tr>

      {open && (
        <tr className="bg-slate-50 dark:bg-slate-800/30">
          <td />
          <td colSpan={metrics.length + 2} className="px-4 pb-4 pt-2">
            <div className="space-y-3 text-sm">

              {/* Answer */}
              <div>
                <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1">คำตอบจาก LLM</p>
                <p className="text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-900 rounded-xl px-3 py-2 border border-slate-200 dark:border-slate-700 whitespace-pre-wrap leading-relaxed">
                  {sample.response}
                </p>
              </div>

              {/* Reference */}
              {sample.reference && (
                <div>
                  <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1">Ground Truth</p>
                  <p className="text-slate-700 dark:text-slate-300 bg-emerald-50 dark:bg-emerald-950/20 rounded-xl px-3 py-2 border border-emerald-200 dark:border-emerald-900">
                    {sample.reference}
                  </p>
                </div>
              )}

              {/* Contexts */}
              {sample.retrieved_contexts?.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1">
                    <BookOpen size={11} className="inline mr-1" />
                    Context ที่ดึงมา ({sample.retrieved_contexts.length} chunks)
                  </p>
                  <div className="space-y-1.5 max-h-48 overflow-y-auto">
                    {sample.retrieved_contexts.map((ctx, ci) => (
                      <p key={ci} className="text-xs text-slate-600 dark:text-slate-400 bg-white dark:bg-slate-900 rounded-lg px-3 py-2 border border-slate-200 dark:border-slate-700 line-clamp-3">
                        <span className="font-semibold text-indigo-500 mr-1">[{ci + 1}]</span>
                        {ctx.slice(0, 200)}{ctx.length > 200 ? "…" : ""}
                      </p>
                    ))}
                  </div>
                </div>
              )}

            </div>
          </td>
        </tr>
      )}
    </>
  );
}

// ── Upload zone ───────────────────────────────────────────────────────────────
function UploadZone({ onLoad, label }: { onLoad: (r: EvalResult) => void; label: string }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFile = useCallback((file: File) => {
    setError(null);
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        // Python's json.dump writes bare NaN/Infinity tokens which JSON.parse
        // rejects. Replace them with null before parsing so any older result
        // file (including copies saved elsewhere) still loads.
        const raw = (e.target?.result as string)
          .replace(/:\s*NaN\b/g, ": null")
          .replace(/:\s*-?Infinity\b/g, ": null");
        const data = JSON.parse(raw) as EvalResult;
        if (!data.aggregate || !Array.isArray(data.samples))
          throw new Error("ไฟล์ไม่ถูกต้อง — ต้องมี aggregate และ samples");
        // Back-fill metrics list if missing (older format)
        if (!Array.isArray(data.metrics)) {
          data.metrics = Object.keys(data.aggregate);
        }
        onLoad(data);
      } catch (err) {
        setError((err as Error).message);
      }
    };
    reader.readAsText(file);
  }, [onLoad]);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  return (
    <div
      onDrop={onDrop}
      onDragOver={(e) => e.preventDefault()}
      onClick={() => inputRef.current?.click()}
      className="flex flex-col items-center justify-center gap-3 p-8 rounded-2xl border-2 border-dashed border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 cursor-pointer hover:border-indigo-400 dark:hover:border-indigo-500 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-all"
    >
      <input
        ref={inputRef}
        type="file"
        accept=".json"
        className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
      />
      <div className="w-10 h-10 rounded-xl bg-indigo-50 dark:bg-indigo-900/30 flex items-center justify-center">
        <FileJson size={20} className="text-indigo-500" />
      </div>
      <div className="text-center">
        <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">{label}</p>
        <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
          คลิกหรือลากไฟล์ JSON จาก <code className="font-mono">eval/results/</code>
        </p>
      </div>
      {error && (
        <div className="flex items-center gap-1.5 text-xs text-red-600 dark:text-red-400">
          <AlertCircle size={12} /> {error}
        </div>
      )}
    </div>
  );
}

// ── Result panel ──────────────────────────────────────────────────────────────
function ResultPanel({ result, onClear }: { result: EvalResult; onClear: () => void }) {
  const ts = result.timestamp
    ? new Date(
        result.timestamp.replace(
          /^(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})$/,
          "$1-$2-$3T$4:$5:$6"
        )
      ).toLocaleString("th-TH")
    : "—";

  return (
    <div className="space-y-5">
      {/* Run info */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 text-sm">
        <div className="flex items-center gap-3">
          <span className="px-2 py-0.5 rounded-md bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-400 text-xs font-mono font-semibold">
            {result.company}
          </span>
          <span className="text-slate-500 dark:text-slate-400 text-xs">{ts}</span>
          <span className="text-slate-500 dark:text-slate-400 text-xs">{result.n_samples} คำถาม</span>
          <span className="text-slate-500 dark:text-slate-400 text-xs">{result.metrics.length} metrics</span>
        </div>
        <button onClick={onClear} className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors">
          <X size={14} />
        </button>
      </div>

      {/* Aggregate scores */}
      <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700">
        <h2 className="text-sm font-bold text-slate-700 dark:text-slate-200 mb-4">Aggregate Scores</h2>
        <div className="space-y-3">
          {Object.entries(result.aggregate).map(([key, score]) => (
            <ScoreBar key={key} label={metricLabel(key)} score={score} />
          ))}
        </div>
      </div>

      {/* Per-question table */}
      <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-200 dark:border-slate-700">
          <h2 className="text-sm font-bold text-slate-700 dark:text-slate-200">ผลรายคำถาม</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-700">
                <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-400 w-8">#</th>
                <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 dark:text-slate-400">คำถาม</th>
                {result.metrics.map((m) => (
                  <th key={m} className="px-4 py-2.5 text-center text-xs font-semibold text-slate-500 dark:text-slate-400 whitespace-nowrap">
                    {metricLabel(m)}
                  </th>
                ))}
                <th className="px-4 py-2.5 text-center text-xs font-semibold text-slate-500 dark:text-slate-400">เฉลี่ย</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {result.samples.map((sample, i) => (
                <QuestionRow key={i} sample={sample} metrics={result.metrics} idx={i} />
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ── Compare view ──────────────────────────────────────────────────────────────
function CompareView({ a, b }: { a: EvalResult; b: EvalResult }) {
  const allMetrics = Array.from(new Set([...Object.keys(a.aggregate), ...Object.keys(b.aggregate)]));
  return (
    <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 overflow-hidden">
      <div className="px-5 py-3 border-b border-slate-200 dark:border-slate-700">
        <h2 className="text-sm font-bold text-slate-700 dark:text-slate-200">เปรียบเทียบ</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-700">
              <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 dark:text-slate-400">Metric</th>
              <th className="px-4 py-2.5 text-center text-xs font-semibold text-indigo-600 dark:text-indigo-400">
                {a.company} · {a.timestamp.slice(0, 8)}
              </th>
              <th className="px-4 py-2.5 text-center text-xs font-semibold text-violet-600 dark:text-violet-400">
                {b.company} · {b.timestamp.slice(0, 8)}
              </th>
              <th className="px-4 py-2.5 text-center text-xs font-semibold text-slate-500 dark:text-slate-400">Δ</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {allMetrics.map((m) => {
              const sa = a.aggregate[m];
              const sb = b.aggregate[m];
              const diff = (sa != null && sb != null && typeof sa === "number" && typeof sb === "number") ? sb - sa : null;
              return (
                <tr key={m} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                  <td className="px-4 py-3 text-sm text-slate-700 dark:text-slate-300">{metricLabel(m)}</td>
                  <td className="px-4 py-3 text-center">
                    {sa != null ? <ScoreBadge score={sa} /> : <span className="text-slate-400 text-xs">—</span>}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {sb != null ? <ScoreBadge score={sb} /> : <span className="text-slate-400 text-xs">—</span>}
                  </td>
                  <td className="px-4 py-3 text-center text-xs font-mono font-semibold">
                    {diff != null ? (
                      <span className={diff > 0 ? "text-emerald-600 dark:text-emerald-400" : diff < 0 ? "text-red-600 dark:text-red-400" : "text-slate-400"}>
                        {diff > 0 ? "+" : ""}{diff.toFixed(3)}
                      </span>
                    ) : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function EvalPage() {
  const [resultA, setResultA] = useState<EvalResult | null>(null);
  const [resultB, setResultB] = useState<EvalResult | null>(null);
  const [compareMode, setCompareMode] = useState(false);

  const isEmpty = !resultA;

  return (
    <div className="space-y-5">

      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center shadow-sm shadow-indigo-600/40">
            <FlaskConical size={18} className="text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-900 dark:text-white leading-none">
              RAG Evaluation
            </h1>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              ดูผล Ragas evaluation จากไฟล์ <code className="font-mono">eval/results/*.json</code>
            </p>
          </div>
        </div>

        {resultA && (
          <button
            onClick={() => { setCompareMode(!compareMode); if (!compareMode) setResultB(null); }}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-xl border text-sm font-medium transition-all ${
              compareMode
                ? "bg-violet-600 border-violet-600 text-white"
                : "border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
            }`}
          >
            <GitCompare size={14} />
            เปรียบเทียบ 2 runs
          </button>
        )}
      </div>

      {/* Upload zones */}
      {isEmpty ? (
        <UploadZone onLoad={setResultA} label="อัปโหลดผล Evaluation (Run A)" />
      ) : compareMode && !resultB ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-3 rounded-xl border border-indigo-200 dark:border-indigo-800 bg-indigo-50 dark:bg-indigo-950/20 text-xs text-indigo-600 dark:text-indigo-400 font-medium">
            Run A: {resultA.company} · {resultA.timestamp}
          </div>
          <UploadZone onLoad={setResultB} label="อัปโหลด Run B เพื่อเปรียบเทียบ" />
        </div>
      ) : null}

      {/* Results */}
      {resultA && !compareMode && (
        <ResultPanel result={resultA} onClear={() => { setResultA(null); setResultB(null); }} />
      )}

      {compareMode && resultA && resultB && (
        <div className="space-y-5">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <div>
              <p className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 mb-2">Run A</p>
              <ResultPanel result={resultA} onClear={() => { setResultA(null); setResultB(null); setCompareMode(false); }} />
            </div>
            <div>
              <p className="text-xs font-semibold text-violet-600 dark:text-violet-400 mb-2">Run B</p>
              <ResultPanel result={resultB} onClear={() => setResultB(null)} />
            </div>
          </div>
          <CompareView a={resultA} b={resultB} />
        </div>
      )}

      {/* Empty state hint */}
      {isEmpty && (
        <div className="text-center py-6 text-slate-400 dark:text-slate-600 text-sm space-y-1">
          <p>รัน evaluation ก่อน แล้วค่อยอัปโหลดผล:</p>
          <code className="text-xs bg-slate-100 dark:bg-slate-800 px-3 py-1 rounded-lg">
            cd backend && python -m eval.ragas_eval
          </code>
        </div>
      )}

    </div>
  );
}
