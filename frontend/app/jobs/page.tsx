"use client";

import { useState, useEffect, useCallback } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8080";
const DEFAULT_COMPANY = process.env.NEXT_PUBLIC_COMPANY_CODE || "DEVES";

const STATUS_COLORS: Record<string, string> = {
  pending:    "bg-yellow-100 text-yellow-700",
  processing: "bg-blue-100 text-blue-700",
  completed:  "bg-green-100 text-green-700",
  failed:     "bg-red-100 text-red-700",
};

const STATUS_ICONS: Record<string, string> = {
  pending: "⏳", processing: "🔄", completed: "✅", failed: "❌",
};

export default function JobsPage() {
  const [jobs, setJobs] = useState<any[]>([]);
  const [company, setCompany] = useState(DEFAULT_COMPANY);
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [expandId, setExpandId] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ limit: "50" });
      if (statusFilter) params.set("status", statusFilter);
      if (company) params.set("company_code", company);
      const res = await fetch(`${API_BASE}/api/jobs?${params}`);
      const data = await res.json();
      setJobs(data.items || []);
    } finally {
      setLoading(false);
    }
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
      await fetch(`${API_BASE}/api/jobs/crawl-all?company_code=${company}`, { method: "POST" });
      setTimeout(load, 1000);
    } finally {
      setTriggering(false);
    }
  }

  async function runPending() {
    await fetch(`${API_BASE}/api/jobs/run-pending`, { method: "POST" });
    setTimeout(load, 1000);
  }

  async function deleteJob(id: string) {
    await fetch(`${API_BASE}/api/jobs/${id}`, { method: "DELETE" });
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
      <div className="rounded-2xl bg-white p-5 shadow-sm flex flex-wrap items-center gap-4">
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-slate-800">⚙️ Job Monitor</h1>
          <div className="flex gap-2 mt-1 flex-wrap">
            {Object.entries(STATUS_ICONS).map(([s, icon]) => (
              <span key={s} className={`text-xs px-2 py-0.5 rounded-full ${STATUS_COLORS[s]}`}>
                {icon} {s}: {counts[s] || 0}
              </span>
            ))}
          </div>
        </div>
        <div className="flex gap-2 flex-wrap items-center">
          <select value={company} onChange={(e) => setCompany(e.target.value)} className="rounded-lg border px-3 py-1.5 text-sm">
            <option value="DEVES">DEVES</option>
            <option value="LOCKTON">LOCKTON</option>
          </select>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="rounded-lg border px-3 py-1.5 text-sm">
            <option value="">ทุก status</option>
            <option value="pending">Pending</option>
            <option value="processing">Processing</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
          </select>
          <label className="flex items-center gap-1.5 text-sm text-slate-600 cursor-pointer">
            <input type="checkbox" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} className="rounded" />
            Auto refresh
          </label>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3 flex-wrap">
        <button onClick={triggerCrawl} disabled={triggering} className="rounded-xl bg-slate-800 px-4 py-2 text-sm text-white hover:bg-slate-700 disabled:opacity-50">
          {triggering ? "🔄 กำลัง Crawl…" : "🕷️ Crawl All Sources"}
        </button>
        <button onClick={runPending} className="rounded-xl border px-4 py-2 text-sm hover:bg-slate-50">
          ▶️ Run Pending Jobs
        </button>
        <button onClick={load} className="rounded-xl border px-4 py-2 text-sm hover:bg-slate-50">
          🔃 Refresh
        </button>
      </div>

      {/* Jobs table */}
      <div className="rounded-2xl bg-white shadow-sm overflow-hidden">
        <div className="p-3 border-b bg-slate-50 text-xs font-semibold text-slate-500 uppercase tracking-wide">
          Jobs ({jobs.length})
        </div>
        {loading ? (
          <div className="p-10 text-center text-slate-400">กำลังโหลด…</div>
        ) : jobs.length === 0 ? (
          <div className="p-10 text-center text-slate-400 text-sm">ไม่มี job</div>
        ) : (
          <div>
            {jobs.map((job) => (
              <div key={job.id} className="border-b">
                <div
                  className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-slate-50"
                  onClick={() => setExpandId(expandId === job.id ? null : job.id)}
                >
                  <span className="text-lg">{STATUS_ICONS[job.status] || "📋"}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-800">{job.job_type}</p>
                    <p className="text-xs text-slate-400 truncate">
                      {job.payload?.url || job.payload?._filename || job.id}
                    </p>
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[job.status] || "bg-slate-100"}`}>
                    {job.status}
                  </span>
                  <span className="text-xs text-slate-400 shrink-0">{fmt(job.created_at)}</span>
                  <button
                    onClick={(e) => { e.stopPropagation(); deleteJob(job.id); }}
                    className="text-xs px-2 py-1 rounded-lg border border-red-200 text-red-500 hover:bg-red-50 shrink-0"
                  >
                    🗑️
                  </button>
                </div>

                {expandId === job.id && (
                  <div className="px-4 pb-4 pt-1 bg-slate-50">
                    {job.message && (
                      <div className="mb-2 rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-700">
                        {job.message}
                      </div>
                    )}
                    <pre className="text-xs text-slate-600 whitespace-pre-wrap max-h-48 overflow-auto rounded-lg bg-white border p-3">
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
