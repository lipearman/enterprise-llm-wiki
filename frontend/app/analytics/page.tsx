"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import { LayoutDashboard, FileText, MessageSquareOff, Cpu, FlaskConical, ScrollText, RefreshCw } from "lucide-react";

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

export default function AnalyticsPage() {
  const [data, setData] = useState<Overview | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try { setData(await apiFetch("/api/analytics/overview").then(r => r.json())); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

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
        </>
      )}
    </div>
  );
}
