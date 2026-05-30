"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import {
  ClipboardList, RefreshCw, Filter, ChevronLeft, ChevronRight,
  ChevronDown, ChevronUp, Clock,
} from "lucide-react";

const LIMIT = 50;

const DEFAULT_COMPANY = process.env.NEXT_PUBLIC_COMPANY_CODE || "DEVES";

const inputCls =
  "rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 " +
  "text-slate-800 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-500 " +
  "px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500";

// ── Action badge colours ───────────────────────────────────────────────────────
function actionColor(action: string): string {
  if (action.startsWith("auth"))        return "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400";
  if (action.startsWith("chat"))        return "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400";
  if (action.startsWith("source"))      return "bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-400";
  if (action.startsWith("unanswered"))  return "bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400";
  if (action.startsWith("job"))         return "bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400";
  return "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400";
}

function statusColor(status: string): string {
  if (status === "ok")    return "bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400";
  if (status === "fail")  return "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400";
  if (status === "error") return "bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400";
  return "bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400";
}

// ── Detail expander ───────────────────────────────────────────────────────────
function DetailCell({ detail }: { detail: Record<string, unknown> }) {
  const [open, setOpen] = useState(false);
  const keys = Object.keys(detail);
  if (keys.length === 0) return <span className="text-slate-400 text-xs">—</span>;
  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 text-xs text-indigo-600 dark:text-indigo-400 hover:underline"
      >
        {open ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
        {open ? "ซ่อน" : `ดู (${keys.length} fields)`}
      </button>
      {open && (
        <pre className="mt-1.5 text-[11px] bg-slate-50 dark:bg-slate-800 rounded-lg px-3 py-2 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 whitespace-pre-wrap leading-relaxed max-w-xs overflow-auto">
          {JSON.stringify(detail, null, 2)}
        </pre>
      )}
    </div>
  );
}

// ── Types ─────────────────────────────────────────────────────────────────────
interface AuditItem {
  id:           string;
  created_at:   string;
  client_ip:    string | null;
  api_key_tag:  string | null;
  company_code: string | null;
  action:       string;
  http_method:  string | null;
  path:         string | null;
  status:       string;
  status_code:  number;
  detail:       Record<string, unknown>;
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function AuditPage() {
  const [items,    setItems]    = useState<AuditItem[]>([]);
  const [total,    setTotal]    = useState(0);
  const [loading,  setLoading]  = useState(false);
  const [page,     setPage]     = useState(0);
  const [company,  setCompany]  = useState(DEFAULT_COMPANY);
  const [action,   setAction]   = useState("");
  const [status,   setStatus]   = useState("");

  const fetchItems = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        limit:  String(LIMIT),
        offset: String(page * LIMIT),
      });
      if (company) params.set("company_code", company);
      if (action)  params.set("action", action);
      if (status)  params.set("status", status);

      const res  = await apiFetch(`/api/audit/logs?${params}`);
      const data = await res.json();
      setItems(data.items ?? []);
      setTotal(data.total ?? 0);
    } finally {
      setLoading(false);
    }
  }, [company, action, status, page]);

  useEffect(() => { fetchItems(); }, [fetchItems]);

  const totalPages = Math.ceil(total / LIMIT);

  return (
    <div className="space-y-5">

      {/* ── Header ── */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center shadow-sm shadow-indigo-600/40">
            <ClipboardList size={18} className="text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-900 dark:text-white leading-none">
              Audit Logs
            </h1>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              บันทึกการกระทำทั้งหมดในระบบ ·{" "}
              <span className="font-semibold text-indigo-500">{total.toLocaleString()}</span> รายการ
            </p>
          </div>
        </div>
        <button
          onClick={fetchItems}
          className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
        >
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
          รีเฟรช
        </button>
      </div>

      {/* ── Filters ── */}
      <div className="flex flex-wrap items-center gap-3 p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 shadow-sm">
        <Filter size={14} className="text-slate-400 shrink-0" />

        <input
          value={company}
          onChange={(e) => { setCompany(e.target.value.toUpperCase()); setPage(0); }}
          placeholder="รหัสบริษัท"
          className={`${inputCls} w-36`}
        />

        <select
          value={action}
          onChange={(e) => { setAction(e.target.value); setPage(0); }}
          className={`${inputCls} w-48`}
        >
          <option value="">ทุก action</option>
          <option value="auth">auth.*</option>
          <option value="chat">chat.*</option>
          <option value="source">source.*</option>
          <option value="unanswered">unanswered.*</option>
          <option value="job">job.*</option>
          <option value="auth.login">auth.login</option>
          <option value="chat.question">chat.question</option>
          <option value="source.add_url">source.add_url</option>
          <option value="source.add_file">source.add_file</option>
          <option value="source.delete">source.delete</option>
          <option value="unanswered.resolve">unanswered.resolve</option>
          <option value="unanswered.delete">unanswered.delete</option>
          <option value="job.crawl_all">job.crawl_all</option>
        </select>

        <select
          value={status}
          onChange={(e) => { setStatus(e.target.value); setPage(0); }}
          className={`${inputCls} w-36`}
        >
          <option value="">ทุก status</option>
          <option value="ok">ok</option>
          <option value="fail">fail</option>
          <option value="error">error</option>
        </select>
      </div>

      {/* ── Table ── */}
      <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-40 text-slate-400 dark:text-slate-600 text-sm">
            กำลังโหลด…
          </div>
        ) : items.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-40 gap-2 text-slate-400 dark:text-slate-600">
            <ClipboardList size={32} />
            <p className="text-sm">ไม่มีบันทึก</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 w-36">เวลา</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 w-44">Action</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 w-24">บริษัท</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 w-32">IP</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 w-28">API Key</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 w-20">Status</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400">Detail</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {items.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">

                    {/* Time */}
                    <td className="px-4 py-3 text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap">
                      <div className="flex items-center gap-1">
                        <Clock size={11} />
                        {new Date(item.created_at).toLocaleDateString("th-TH", {
                          day: "2-digit", month: "short", year: "2-digit",
                        })}
                      </div>
                      <div className="text-[10px] text-slate-400 dark:text-slate-600 mt-0.5">
                        {new Date(item.created_at).toLocaleTimeString("th-TH", {
                          hour: "2-digit", minute: "2-digit", second: "2-digit",
                        })}
                      </div>
                    </td>

                    {/* Action */}
                    <td className="px-4 py-3">
                      <span className={`inline-block px-2 py-0.5 rounded-md text-xs font-mono font-medium ${actionColor(item.action)}`}>
                        {item.action}
                      </span>
                    </td>

                    {/* Company */}
                    <td className="px-4 py-3">
                      <span className="inline-block px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-xs font-mono text-slate-600 dark:text-slate-400">
                        {item.company_code ?? "—"}
                      </span>
                    </td>

                    {/* IP */}
                    <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-400 font-mono">
                      {item.client_ip ?? "—"}
                    </td>

                    {/* API Key tag */}
                    <td className="px-4 py-3 text-xs text-slate-500 dark:text-slate-500 font-mono">
                      {item.api_key_tag ?? "—"}
                    </td>

                    {/* Status */}
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${statusColor(item.status)}`}>
                        {item.status}
                      </span>
                    </td>

                    {/* Detail */}
                    <td className="px-4 py-3">
                      <DetailCell detail={item.detail ?? {}} />
                    </td>

                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Pagination ── */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-sm text-slate-500 dark:text-slate-400">
          <span>
            แสดง {page * LIMIT + 1}–{Math.min((page + 1) * LIMIT, total)} จาก {total.toLocaleString()} รายการ
          </span>
          <div className="flex gap-1">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 disabled:opacity-40 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            >
              <ChevronLeft size={15} />
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 disabled:opacity-40 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            >
              <ChevronRight size={15} />
            </button>
          </div>
        </div>
      )}

    </div>
  );
}
