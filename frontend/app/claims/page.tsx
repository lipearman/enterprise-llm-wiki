"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { apiFetch } from "@/lib/api";
import { FileWarning, RefreshCw, Car, CalendarDays, Phone, Hash, Check, X, Search } from "lucide-react";

interface Claim {
  reference: string | null;
  policy_number: string | null;
  vehicle: string | null;
  incident: string | null;
  incident_date: string | null;
  callback_phone: string | null;
  review_status: string;
  created_at: string | null;
}

const STATUSES = [
  { key: "submitted",  label: "ส่งแล้ว" },
  { key: "collecting", label: "กำลังกรอก" },
  { key: "cancelled",  label: "ยกเลิก" },
];

const REVIEW_META: Record<string, { label: string; cls: string }> = {
  received:  { label: "รับเรื่อง",     cls: "bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300" },
  reviewing: { label: "กำลังพิจารณา",  cls: "bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300" },
  approved:  { label: "อนุมัติ",       cls: "bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300" },
  rejected:  { label: "ปฏิเสธ",        cls: "bg-rose-100 dark:bg-rose-900/40 text-rose-700 dark:text-rose-300" },
};

export default function ClaimsPage() {
  const [status, setStatus] = useState("submitted");
  const [data, setData] = useState<{ count: number; items: Claim[] } | null>(null);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<Record<string, boolean>>({});
  const reqRef = useRef(0);

  const load = useCallback(async () => {
    const my = ++reqRef.current;          // guard against out-of-order responses
    setLoading(true);
    try {
      const [d, c] = await Promise.all([
        apiFetch(`/api/claims?status=${status}`).then(r => r.json()),
        apiFetch(`/api/claims/counts`).then(r => r.json()).catch(() => ({})),
      ]);
      if (my === reqRef.current) { setData(d); setCounts(c); }
    } finally { if (my === reqRef.current) setLoading(false); }
  }, [status]);
  useEffect(() => { load(); }, [load]);

  const setReview = async (ref: string, newStatus: string) => {
    setBusy(b => ({ ...b, [ref]: true }));
    try {
      await apiFetch(`/api/claims/${encodeURIComponent(ref)}/status`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus }),
      });
      setData(d => d ? { ...d, items: d.items.map(c => c.reference === ref ? { ...c, review_status: newStatus } : c) } : d);
    } finally { setBusy(b => ({ ...b, [ref]: false })); }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center shadow-sm shadow-indigo-600/40">
            <FileWarning size={18} className="text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-900 dark:text-white leading-none">Claims</h1>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">รายการแจ้งเคลมจากลูกค้า {data ? `· ${data.count} รายการ` : ""}</p>
          </div>
        </div>
        <button onClick={load} className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800">
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} /> รีเฟรช
        </button>
      </div>

      {/* status filter (with per-status counts) */}
      <div className="flex gap-1.5">
        {STATUSES.map(s => (
          <button key={s.key} onClick={() => setStatus(s.key)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              status === s.key ? "bg-indigo-600 text-white" : "bg-slate-100 dark:bg-slate-800 text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-700"
            }`}>{s.label}{counts[s.key] != null ? ` (${counts[s.key]})` : ""}</button>
        ))}
      </div>

      {!data ? (
        <p className="text-sm text-slate-400 text-center py-10">{loading ? "กำลังโหลด…" : "ไม่มีข้อมูล"}</p>
      ) : data.items.length === 0 ? (
        <div className="text-center py-16 text-slate-400">
          <FileWarning size={36} className="mx-auto mb-2 opacity-50" />
          <p className="text-sm">ยังไม่มีเคลมสถานะนี้</p>
          <p className="text-[11px] mt-1">เปิด <code>ENABLE_CLAIM_INTAKE</code> + รัน <code>sql/011</code> เพื่อเก็บถาวร</p>
        </div>
      ) : (
        <div className="space-y-2">
          {data.items.map((c, i) => (
            <div key={c.reference ?? i} className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4">
              <div className="flex items-center justify-between gap-2">
                <span className="flex items-center gap-1.5 font-mono text-sm font-semibold text-indigo-600 dark:text-indigo-400"><Hash size={13} />{c.reference ?? "—"}</span>
                <div className="flex items-center gap-2">
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${REVIEW_META[c.review_status]?.cls ?? REVIEW_META.received.cls}`}>{REVIEW_META[c.review_status]?.label ?? c.review_status}</span>
                  <span className="text-[11px] text-slate-400">{c.created_at?.slice(0, 19).replace("T", " ")}</span>
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1 mt-2 text-xs">
                <div className="text-slate-600 dark:text-slate-300"><span className="text-slate-400">กรมธรรม์:</span> {c.policy_number ?? "—"}</div>
                <div className="flex items-center gap-1 text-slate-600 dark:text-slate-300"><Car size={12} className="text-slate-400" /> {c.vehicle ?? "—"}</div>
                <div className="flex items-center gap-1 text-slate-600 dark:text-slate-300"><CalendarDays size={12} className="text-slate-400" /> {c.incident_date ?? "—"}</div>
                <div className="flex items-center gap-1 text-slate-600 dark:text-slate-300"><Phone size={12} className="text-slate-400" /> {c.callback_phone ?? "—"}</div>
              </div>
              {c.incident && <p className="text-xs text-slate-500 dark:text-slate-400 mt-1.5 border-t border-slate-100 dark:border-slate-800 pt-1.5">📝 {c.incident}</p>}
              {/* handling workflow actions */}
              {c.reference && (
                <div className="flex items-center gap-1.5 mt-2.5">
                  {c.review_status === "received" && (
                    <button onClick={() => setReview(c.reference!, "reviewing")} disabled={busy[c.reference]}
                      className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-blue-600 text-white text-xs hover:bg-blue-700 disabled:opacity-40"><Search size={12} /> เริ่มพิจารณา</button>
                  )}
                  {c.review_status === "reviewing" && (
                    <>
                      <button onClick={() => setReview(c.reference!, "approved")} disabled={busy[c.reference]}
                        className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-emerald-600 text-white text-xs hover:bg-emerald-700 disabled:opacity-40"><Check size={12} /> อนุมัติ</button>
                      <button onClick={() => setReview(c.reference!, "rejected")} disabled={busy[c.reference]}
                        className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-600 text-slate-500 text-xs hover:bg-rose-50 dark:hover:bg-rose-950/30 hover:text-rose-600 disabled:opacity-40"><X size={12} /> ปฏิเสธ</button>
                    </>
                  )}
                  {(c.review_status === "approved" || c.review_status === "rejected") && (
                    <button onClick={() => setReview(c.reference!, "reviewing")} disabled={busy[c.reference]}
                      className="text-[11px] text-slate-400 hover:text-slate-600 hover:underline">↩ เปิดพิจารณาใหม่</button>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
