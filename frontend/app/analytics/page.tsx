"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import { LayoutDashboard, FileText, MessageSquareOff, Cpu, FlaskConical, ScrollText, RefreshCw, Workflow, ArrowRight, RotateCcw, Trash2 } from "lucide-react";

interface Overview {
  company_code: string;
  content: { wiki_pages: number | null; canonical_qa: number | null; document_chunks: number | null; sources: number | null };
  chat: { unanswered_total: number | null; recent_unanswered: { question: string; resolved: boolean }[] };
  providers: { total: number; active: number; roles_configured: Record<string, number> } | null;
  audit: { recent: { action: string; status: string; at: string }[] } | null;
  eval: { timestamp: string; n_samples: number; aggregate: Record<string, number | null> } | null;
  agentic: { enabled: boolean; planner: boolean; llm_rerank: boolean; graph_hops: number };
}

const METRIC_LABELS: Record<string, string> = {
  faithfulness: "Faithfulness",
  answer_relevancy: "Answer Relevancy",
  context_precision: "Context Precision",
  context_recall: "Context Recall",
  answer_correctness: "Answer Correctness",
};

function Stat({ icon, label, value, sub }: { icon: React.ReactNode; label: string; value: React.ReactNode; sub?: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4">
      <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 text-xs font-medium">{icon}{label}</div>
      <div className="text-2xl font-bold text-slate-900 dark:text-white mt-1">{value}</div>
      {sub && <div className="text-[11px] text-slate-400 mt-0.5">{sub}</div>}
    </div>
  );
}

function bar(v: number | null) {
  if (v == null) return <span className="text-slate-400">n/a</span>;
  const pct = Math.round(v * 100);
  const color = v >= 0.8 ? "bg-emerald-500" : v >= 0.7 ? "bg-amber-500" : "bg-rose-500";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
        <div className={`h-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono text-slate-600 dark:text-slate-300 w-10 text-right">{v.toFixed(2)}</span>
    </div>
  );
}

interface AgentGraph {
  enabled: boolean;
  available: boolean;
  nodes: string[];
  edges: { source: string; target: string; conditional: boolean }[];
}

interface AgentRun {
  question: string;
  at: string;
  duration: number;
  iterations: number;
  steps: { node: string; label: string; t: number }[];
  answer_preview: string;
}

interface RunStats {
  count: number;
  avg_duration: number;
  avg_iterations: number;
  reformulate_pct: number;
}

const NODE_META: Record<string, { label: string; icon: string }> = {
  __start__:   { label: "เริ่ม", icon: "▶️" },
  retrieve:    { label: "ค้นหาข้อมูล", icon: "🔍" },
  generate:    { label: "เรียบเรียงคำตอบ", icon: "✍️" },
  validate:    { label: "ตรวจสอบ", icon: "🔎" },
  reformulate: { label: "ค้นเพิ่มเติม", icon: "🔄" },
  __end__:     { label: "ตอบ", icon: "🏁" },
};

export default function AnalyticsPage() {
  const [data, setData] = useState<Overview | null>(null);
  const [graph, setGraph] = useState<AgentGraph | null>(null);
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [runStats, setRunStats] = useState<RunStats | null>(null);
  const [runSearch, setRunSearch] = useState("");
  const [retentionDays, setRetentionDays] = useState(30);
  const [loading, setLoading] = useState(true);

  const loadRuns = useCallback(async (search: string) => {
    const r = await apiFetch(`/api/analytics/agent-runs?limit=50${search ? `&search=${encodeURIComponent(search)}` : ""}`)
      .then(r => r.json()).catch(() => null);
    setRuns(r?.runs ?? []); setRunStats(r?.stats ?? null);
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [ov, gr] = await Promise.all([
        apiFetch("/api/analytics/overview").then(r => r.json()),
        apiFetch("/api/analytics/agent-graph").then(r => r.json()).catch(() => null),
      ]);
      setData(ov); setGraph(gr);
      await loadRuns("");
    } finally { setLoading(false); }
  }, [loadRuns]);
  useEffect(() => { load(); }, [load]);

  const purgeRuns = async () => {
    if (!confirm(`ลบ run ที่เก่ากว่า ${retentionDays} วัน?`)) return;
    const r = await apiFetch(`/api/analytics/agent-runs?older_than_days=${retentionDays}`, { method: "DELETE" }).then(r => r.json());
    alert(`ลบไป ${r.removed} รายการ`);
    loadRuns(runSearch);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center shadow-sm shadow-indigo-600/40">
            <LayoutDashboard size={18} className="text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-900 dark:text-white leading-none">Analytics</h1>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">ภาพรวมระบบ {data ? `· ${data.company_code}` : ""}</p>
          </div>
        </div>
        <button onClick={load} className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800">
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} /> รีเฟรช
        </button>
      </div>

      {!data ? (
        <p className="text-sm text-slate-400 text-center py-10">{loading ? "กำลังโหลด…" : "ไม่มีข้อมูล"}</p>
      ) : (
        <>
          {/* Content stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Stat icon={<FileText size={13} />} label="Wiki Pages" value={data.content.wiki_pages ?? "—"} />
            <Stat icon={<FileText size={13} />} label="Canonical QA" value={data.content.canonical_qa ?? "—"} />
            <Stat icon={<FileText size={13} />} label="Chunks" value={data.content.document_chunks ?? "—"} />
            <Stat icon={<MessageSquareOff size={13} />} label="Unanswered" value={data.chat.unanswered_total ?? "—"} sub="คำถามที่ตอบไม่ได้" />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Latest eval */}
            <div className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4">
              <h2 className="text-sm font-bold text-slate-700 dark:text-slate-200 mb-3 flex items-center gap-1.5"><FlaskConical size={14} /> Latest RAG Eval {data.eval && <span className="text-[11px] font-normal text-slate-400">· {data.eval.timestamp} · n={data.eval.n_samples}</span>}</h2>
              {data.eval ? (
                <div className="space-y-2">
                  {Object.entries(METRIC_LABELS).map(([k, label]) => (
                    <div key={k} className="grid grid-cols-[140px_1fr] items-center gap-2">
                      <span className="text-xs text-slate-500 dark:text-slate-400">{label}</span>
                      {bar(data.eval!.aggregate[k] ?? null)}
                    </div>
                  ))}
                </div>
              ) : <p className="text-xs text-slate-400">ยังไม่มีผล eval</p>}
            </div>

            {/* Providers + agentic */}
            <div className="space-y-4">
              <div className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4">
                <h2 className="text-sm font-bold text-slate-700 dark:text-slate-200 mb-2 flex items-center gap-1.5"><Cpu size={14} /> AI Providers</h2>
                {data.providers ? (
                  <>
                    <p className="text-sm text-slate-600 dark:text-slate-300">{data.providers.active}/{data.providers.total} active</p>
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {Object.entries(data.providers.roles_configured).map(([role, n]) => (
                        <span key={role} className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300">{role}: {n}</span>
                      ))}
                    </div>
                  </>
                ) : <p className="text-xs text-slate-400">n/a</p>}
              </div>

              <div className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4">
                <h2 className="text-sm font-bold text-slate-700 dark:text-slate-200 mb-2">🤖 Agentic RAG</h2>
                <div className="flex flex-wrap gap-1.5">
                  {[["Agentic loop", data.agentic.enabled], ["Query planner", data.agentic.planner], ["LLM rerank", data.agentic.llm_rerank]].map(([label, on]) => (
                    <span key={label as string} className={`text-[10px] px-2 py-0.5 rounded-full ${on ? "bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300" : "bg-slate-100 dark:bg-slate-800 text-slate-400"}`}>{label as string} {on ? "ON" : "OFF"}</span>
                  ))}
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-500">graph hops: {data.agentic.graph_hops}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Recent audit */}
          {data.audit && data.audit.recent.length > 0 && (
            <div className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4">
              <h2 className="text-sm font-bold text-slate-700 dark:text-slate-200 mb-2 flex items-center gap-1.5"><ScrollText size={14} /> Recent Activity</h2>
              <div className="space-y-1">
                {data.audit.recent.map((a, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    <span className={`w-1.5 h-1.5 rounded-full ${a.status === "ok" ? "bg-emerald-500" : "bg-rose-500"}`} />
                    <span className="font-mono text-slate-600 dark:text-slate-300">{a.action}</span>
                    <span className="text-slate-400 ml-auto">{a.at?.slice(0, 19).replace("T", " ")}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Agent graph (Phase 7) */}
          {graph && graph.available && (
            <div className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4">
              <h2 className="text-sm font-bold text-slate-700 dark:text-slate-200 mb-3 flex items-center gap-1.5">
                <Workflow size={14} /> Agent Graph (LangGraph)
                <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${graph.enabled ? "bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300" : "bg-slate-100 dark:bg-slate-800 text-slate-400"}`}>{graph.enabled ? "ACTIVE" : "OFF"}</span>
              </h2>
              {/* main pipeline */}
              <div className="flex flex-wrap items-center gap-1.5">
                {["__start__", "retrieve", "generate", "validate", "__end__"]
                  .filter(n => graph.nodes.includes(n))
                  .map((n, i, arr) => (
                    <span key={n} className="flex items-center gap-1.5">
                      <span className="px-2.5 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-xs font-medium text-slate-700 dark:text-slate-200 whitespace-nowrap">
                        {NODE_META[n]?.icon} {NODE_META[n]?.label ?? n}
                      </span>
                      {i < arr.length - 1 && <ArrowRight size={14} className="text-slate-400 shrink-0" />}
                    </span>
                  ))}
              </div>
              {/* conditional loop */}
              {graph.nodes.includes("reformulate") && (
                <div className="mt-3 flex items-center gap-2 text-xs text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/30 rounded-lg px-3 py-2">
                  <RotateCcw size={13} className="shrink-0" />
                  <span>เงื่อนไข: ถ้า <b>ตรวจสอบ</b> แล้วข้อมูลไม่ครบ → <b>{NODE_META.reformulate.icon} ค้นเพิ่มเติม</b> → วนกลับไป <b>ค้นหา</b> (สูงสุดตาม AGENTIC_MAX_ITERS)</span>
                </div>
              )}
              <p className="text-[11px] text-slate-400 mt-2">{graph.nodes.length} nodes · {graph.edges.length} edges {graph.edges.some(e => e.conditional) ? `· ${graph.edges.filter(e => e.conditional).length} conditional` : ""}</p>
            </div>
          )}

          {/* Recent agent runs (Phase 7) */}
          {(runs.length > 0 || runSearch) && (
            <div className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4">
              <div className="flex items-center justify-between gap-2 mb-3 flex-wrap">
                <h2 className="text-sm font-bold text-slate-700 dark:text-slate-200 flex items-center gap-1.5"><Workflow size={14} /> Recent Agent Runs</h2>
                <div className="flex items-center gap-2">
                  <input value={runSearch} onChange={e => setRunSearch(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && loadRuns(runSearch)}
                    placeholder="ค้นหาคำถาม…"
                    className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 px-2.5 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500 w-36" />
                  <button onClick={() => loadRuns(runSearch)} className="px-2.5 py-1.5 rounded-lg bg-indigo-600 text-white text-xs hover:bg-indigo-700">ค้นหา</button>
                </div>
              </div>

              {/* stats */}
              {runStats && runStats.count > 0 && (
                <div className="flex flex-wrap gap-2 mb-3">
                  {[
                    ["จำนวน run", `${runStats.count}`],
                    ["เฉลี่ย/run", `${runStats.avg_duration}s`],
                    ["เฉลี่ยรอบ", `${runStats.avg_iterations}`],
                    ["ต้อง reformulate", `${runStats.reformulate_pct}%`],
                  ].map(([label, val]) => (
                    <div key={label} className="rounded-xl bg-slate-50 dark:bg-slate-800 px-3 py-1.5">
                      <div className="text-[10px] text-slate-400">{label}</div>
                      <div className="text-sm font-bold text-slate-800 dark:text-white">{val}</div>
                    </div>
                  ))}
                  {/* retention */}
                  <div className="rounded-xl bg-slate-50 dark:bg-slate-800 px-3 py-1.5 flex items-center gap-1.5 ml-auto">
                    <span className="text-[10px] text-slate-400">ลบเก่ากว่า</span>
                    <input type="number" value={retentionDays} min={0} onChange={e => setRetentionDays(Number(e.target.value))}
                      className="w-12 rounded border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 text-xs px-1 py-0.5 text-center" />
                    <span className="text-[10px] text-slate-400">วัน</span>
                    <button onClick={purgeRuns} className="ml-1 p-1 rounded text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/30 hover:text-rose-600" title="ลบ run เก่า"><Trash2 size={13} /></button>
                  </div>
                </div>
              )}

              {runs.length === 0 ? <p className="text-xs text-slate-400">ไม่พบ run ที่ตรงคำค้น</p> : (
              <div className="space-y-3">
                {runs.map((r, i) => (
                  <div key={i} className="border-b border-slate-100 dark:border-slate-800 last:border-0 pb-3 last:pb-0">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm text-slate-700 dark:text-slate-200 truncate">💬 {r.question}</span>
                      <span className="text-[11px] text-slate-400 shrink-0 whitespace-nowrap">{r.at?.slice(11, 19)} · {r.duration}s · {r.iterations} รอบ</span>
                    </div>
                    {/* step trace */}
                    <div className="flex flex-wrap items-center gap-1 mt-1.5">
                      {r.steps.map((s, j) => (
                        <span key={j} className="flex items-center gap-1">
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 whitespace-nowrap" title={`${s.t}s`}>{s.label}</span>
                          {j < r.steps.length - 1 && <span className="text-slate-300 dark:text-slate-600 text-[10px]">→</span>}
                        </span>
                      ))}
                    </div>
                    {r.answer_preview && <p className="text-[11px] text-slate-400 mt-1 truncate">→ {r.answer_preview}</p>}
                  </div>
                ))}
              </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
