"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch, API_BASE } from "@/lib/api";
import { Settings, Bug, Play, RefreshCw, ChevronDown, ChevronUp, Trash2 } from "lucide-react";

const DEFAULT_COMPANY = process.env.NEXT_PUBLIC_COMPANY_CODE || "DEVES";

const STATUS_STYLE: Record<string, string> = {
  pending:    "bg-amber-100  dark:bg-amber-900/40  text-amber-700  dark:text-amber-400",
  processing: "bg-blue-100   dark:bg-blue-900/40   text-blue-700   dark:text-blue-400",
  completed:  "bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-400",
  failed:     "bg-red-100    dark:bg-red-900/40    text-red-700    dark:text-red-400",
};

const STATUS_ICONS: Record<string, string> = {
  pending: "⏳", processing: "🔄", completed: "✅", failed: "❌",
};

export default function JobsPage() {
  const [jobs,         setJobs]         = useState<any[]>([]);
  const [company,      setCompany]      = useState(DEFAULT_COMPANY);
  const [statusFilter, setStatusFilter] = useState("");
  const [loading,      setLoading]      = useState(false);
  const [triggering,   setTriggering]   = useState(false);
  const [expandId,     setExpandId]     = useState<string | null>(null);
  const [autoRefresh,  setAutoRefresh]  = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ limit: "50" });
      if (statusFilter) params.set("status", statusFilter);
      if (company)      params.set("company_code", company);
      const res  = await apiFetch(`${API_BASE}/api/jobs?${params}`);
      const data = await res.json();
      setJobs(data.items || []);
    } finally { setLoading(false); }
  }, [company, statusFilter]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (!autoRefresh) return;
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, [autoRefresh, load]);

  async function triggerCrawl() {
    setTriggering(true);
    try {
      await apiFetch(`${API_BASE}/api/jobs/crawl-all?company_code=${company}`, { method: "POST" });
      setTimeout(load, 1000);
    } finally { setTriggering(false); }
  }

  async function runPending() {
    await apiFetch(`${API_BASE}/api/jobs/run-pending`, { method: "POST" });
    setTimeout(load, 1000);
  }

  async function deleteJob(id: string) {
    await apiFetch(`${API_BASE}/api/jobs/${id}`, { method: "DELETE" });
    load();
  }

  function fmt(ts: string) {
    try { return new Date(ts).toLocaleString("th-TH", { dateStyle: "short", timeStyle: "short" }); }
    catch { return ts; }
  }

  const counts = jobs.reduce((acc, j) => { acc[j.status] = (acc[j.status] || 0) + 1; return acc; }, {} as Record<string, number>);

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 p-5 shadow-sm flex flex-wrap items-center gap-4">
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
            <Settings size={22} className="text-slate-500 dark:text-slate-400" /> Job Monitor
          </h1>
          <div className="flex gap-2 mt-2 flex-wrap">
            {Object.entries(STATUS_ICONS).map(([s, icon]) => (
              <span key={s} className={`text-xs px-2.5 py-1 rounded-full font-medium ${STATUS_STYLE[s]}`}>
                {icon} {s}: {counts[s] || 0}
              </span>
            ))}
          </div>
        </div>
        <div className="flex gap-2 flex-wrap items-center">
          <select value={company} onChange={(e) => setCompany(e.target.value)}
            className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
            <option value="DEVES">DEVES</option>
            <option value="LOCKTON">LOCKTON</option>
          </select>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
            <option value="">ทุก status</option>
            <option value="pending">Pending</option>
            <option value="processing">Processing</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
          </select>
          <label className="flex items-center gap-1.5 text-sm text-slate-600 dark:text-slate-400 cursor-pointer select-none">
            <input type="checkbox" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} className="rounded accent-indigo-600" />
            Auto refresh
          </label>
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex gap-3 flex-wrap">
        <button onClick={triggerCrawl} disabled={triggering}
          className="flex items-center gap-2 rounded-xl bg-slate-900 dark:bg-slate-700 hover:bg-slate-800 dark:hover:bg-slate-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50 transition-colors shadow-sm">
          <Bug size={15} />
          {triggering ? "กำลัง Crawl…" : "Crawl All Sources"}
        </button>
        <button onClick={runPending}
          className="flex items-center gap-2 rounded-xl border border-slate-200 dark:border-slate-700 px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors">
          <Play size={14} /> Run Pending Jobs
        </button>
        <button onClick={load}
          className="flex items-center gap-2 rounded-xl border border-slate-200 dark:border-slate-700 px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} /> Refresh
        </button>
      </div>

      {/* Jobs table */}
      <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
          Jobs ({jobs.length})
        </div>
        {loading ? (
          <div className="p-10 text-center text-slate-400 dark:text-slate-600">กำลังโหลด…</div>
        ) : jobs.length === 0 ? (
          <div className="p-10 text-center text-slate-400 dark:text-slate-600 text-sm">ไม่มี job</div>
        ) : (
          <div>
            {jobs.map((job) => (
              <div key={job.id} className="border-b border-slate-100 dark:border-slate-800/80">
                <div
                  className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
                  onClick={() => setExpandId(expandId === job.id ? null : job.id)}
                >
                  <span className="text-lg shrink-0">{STATUS_ICONS[job.status] || "📋"}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-800 dark:text-slate-200">{job.job_type}</p>
                    <p className="text-xs text-slate-400 dark:text-slate-500 truncate">
                      {job.payload?.url || job.payload?._filename || job.id}
                    </p>
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium shrink-0 ${STATUS_STYLE[job.status] || "bg-slate-100 dark:bg-slate-800 text-slate-500"}`}>
                    {job.status}
                  </span>
                  <span className="text-xs text-slate-400 dark:text-slate-500 shrink-0 hidden sm:block">{fmt(job.created_at)}</span>
                  <div className="flex items-center gap-1 shrink-0">
                    {expandId === job.id
                      ? <ChevronUp size={14} className="text-slate-400" />
                      : <ChevronDown size={14} className="text-slate-400" />}
                    <button
                      onClick={(e) => { e.stopPropagation(); deleteJob(job.id); }}
                      className="flex items-center p-1.5 rounded-lg border border-red-200 dark:border-red-900 text-red-500 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors"
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                </div>

                {expandId === job.id && (
                  <div className="px-4 pb-4 pt-1 bg-slate-50 dark:bg-slate-800/30">
                    {job.message && (
                      <div className="mb-2 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900 px-3 py-2 text-xs text-red-700 dark:text-red-400">
                        {job.message}
                      </div>
                    )}
                    <pre className="text-xs text-slate-600 dark:text-slate-400 whitespace-pre-wrap max-h-48 overflow-auto rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 p-3">
                      {JSON.stringify({ payload: job.payload, result: job.result }, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
