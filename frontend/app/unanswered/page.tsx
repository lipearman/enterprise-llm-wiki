"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import {
  MessageCircleQuestion, CheckCircle2, Trash2, X, ChevronLeft,
  ChevronRight, RefreshCw, Filter, Save, Clock,
} from "lucide-react";

const DEFAULT_COMPANY = process.env.NEXT_PUBLIC_COMPANY_CODE || "DEVES";
const LIMIT = 30;

const inputCls =
  "rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 " +
  "text-slate-800 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-500 " +
  "px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500";

type FilterMode = "open" | "resolved" | "all";

interface UnansweredItem {
  id: string;
  company_code: string;
  question: string;
  session_id: string | null;
  asked_at: string;
  is_resolved: boolean;
  resolved_at: string | null;
  note: string | null;
}

// ── Resolve Modal ──────────────────────────────────────────────────────────────
function ResolveModal({
  item,
  saving,
  onClose,
  onResolve,
}: {
  item: UnansweredItem;
  saving: boolean;
  onClose: () => void;
  onResolve: (note: string) => void;
}) {
  const [note, setNote] = useState(item.note ?? "");

  useEffect(() => {
    const fn = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", fn);
    return () => window.removeEventListener("keydown", fn);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
         onClick={onClose}>
      <div className="w-full max-w-lg rounded-2xl bg-white dark:bg-slate-900 shadow-2xl flex flex-col overflow-hidden"
           onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 dark:border-slate-700 bg-gradient-to-r from-emerald-600 to-teal-600">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={18} className="text-white" />
            <span className="text-sm font-semibold text-white">ทำเครื่องหมายว่าแก้ไขแล้ว</span>
          </div>
          <button onClick={onClose} className="text-white/70 hover:text-white transition-colors">
            <X size={18} />
          </button>
        </div>
        {/* Body */}
        <div className="px-5 py-4 space-y-4">
          <div>
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">คำถาม</p>
            <p className="text-sm text-slate-800 dark:text-slate-200 bg-slate-50 dark:bg-slate-800 rounded-xl px-3 py-2 border border-slate-200 dark:border-slate-700">
              {item.question}
            </p>
          </div>
          <div>
            <label className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1 block">
              หมายเหตุ (ไม่บังคับ)
            </label>
            <textarea
              rows={3}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="เช่น เพิ่มข้อมูลใน Wiki หน้า 'ติดต่อเรา' แล้ว"
              className={`${inputCls} w-full resize-none`}
            />
          </div>
        </div>
        {/* Footer */}
        <div className="flex justify-end gap-2 px-5 py-3 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
          <button onClick={onClose}
            className="px-4 py-2 rounded-xl text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors">
            ยกเลิก
          </button>
          <button
            onClick={() => onResolve(note)}
            disabled={saving}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 transition-colors">
            <Save size={14} />
            {saving ? "กำลังบันทึก…" : "บันทึก"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────────
export default function UnansweredPage() {
  const [items,      setItems]      = useState<UnansweredItem[]>([]);
  const [total,      setTotal]      = useState(0);
  const [unresolved, setUnresolved] = useState(0);
  const [loading,    setLoading]    = useState(false);
  const [page,       setPage]       = useState(0);
  const [filter,     setFilter]     = useState<FilterMode>("open");
  const [company,    setCompany]    = useState(DEFAULT_COMPANY);
  const [resolving,  setResolving]  = useState<UnansweredItem | null>(null);
  const [saving,     setSaving]     = useState(false);

  const fetchItems = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        company_code: company,
        limit: String(LIMIT),
        offset: String(page * LIMIT),
      });
      if (filter !== "all") params.set("is_resolved", filter === "resolved" ? "true" : "false");

      const [listRes, statsRes] = await Promise.all([
        apiFetch(`/api/unanswered?${params}`),
        apiFetch(`/api/unanswered/stats?company_code=${company}`),
      ]);
      const list  = await listRes.json();
      const stats = await statsRes.json();

      setItems(list.items ?? []);
      setTotal(list.total ?? 0);
      setUnresolved(stats.unresolved ?? 0);
    } finally {
      setLoading(false);
    }
  }, [company, filter, page]);

  useEffect(() => { fetchItems(); }, [fetchItems]);

  const handleResolve = async (note: string) => {
    if (!resolving) return;
    setSaving(true);
    try {
      await apiFetch(`/api/unanswered/${resolving.id}/resolve`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ note }),
      });
      setResolving(null);
      fetchItems();
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("ลบคำถามนี้?")) return;
    await apiFetch(`/api/unanswered/${id}`, { method: "DELETE" });
    fetchItems();
  };

  const totalPages = Math.ceil(total / LIMIT);

  const filterBtnCls = (f: FilterMode) =>
    `px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
      filter === f
        ? "bg-indigo-600 text-white"
        : "text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700"
    }`;

  return (
    <div className="space-y-5">
      {/* ── Header ── */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center shadow-sm shadow-indigo-600/40">
            <MessageCircleQuestion size={18} className="text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-900 dark:text-white leading-none">
              คำถามที่ตอบไม่ได้
            </h1>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              จาก Floating Chat · ยังค้างอยู่{" "}
              <span className="font-semibold text-rose-500">{unresolved}</span> รายการ
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

        {/* Status filter */}
        <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800 rounded-xl p-1">
          <button className={filterBtnCls("open")}    onClick={() => { setFilter("open");     setPage(0); }}>
            ยังค้างอยู่
          </button>
          <button className={filterBtnCls("resolved")} onClick={() => { setFilter("resolved"); setPage(0); }}>
            แก้ไขแล้ว
          </button>
          <button className={filterBtnCls("all")}      onClick={() => { setFilter("all");      setPage(0); }}>
            ทั้งหมด
          </button>
        </div>

        {/* Company filter */}
        <input
          value={company}
          onChange={(e) => { setCompany(e.target.value.toUpperCase()); setPage(0); }}
          placeholder="รหัสบริษัท"
          className={`${inputCls} w-36`}
        />
      </div>

      {/* ── Table ── */}
      <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-40 text-slate-400 dark:text-slate-600 text-sm">
            กำลังโหลด…
          </div>
        ) : items.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-40 gap-2 text-slate-400 dark:text-slate-600">
            <CheckCircle2 size={32} />
            <p className="text-sm">ไม่มีคำถามค้าง</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 w-36">วันที่ / เวลา</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 w-24">บริษัท</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400">คำถาม</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 w-28">สถานะ</th>
                <th className="px-4 py-3 w-20"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {items.map((item) => (
                <tr key={item.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
                  {/* Date */}
                  <td className="px-4 py-3 text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap">
                    <div className="flex items-center gap-1">
                      <Clock size={11} />
                      {new Date(item.asked_at).toLocaleDateString("th-TH", {
                        day: "2-digit", month: "short", year: "2-digit",
                      })}
                    </div>
                    <div className="text-[10px] text-slate-400 dark:text-slate-600 mt-0.5">
                      {new Date(item.asked_at).toLocaleTimeString("th-TH", {
                        hour: "2-digit", minute: "2-digit",
                      })}
                    </div>
                  </td>
                  {/* Company */}
                  <td className="px-4 py-3">
                    <span className="inline-block px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-xs font-mono text-slate-600 dark:text-slate-400">
                      {item.company_code}
                    </span>
                  </td>
                  {/* Question */}
                  <td className="px-4 py-3 text-slate-800 dark:text-slate-200">
                    <p className="leading-relaxed">{item.question}</p>
                    {item.note && (
                      <p className="mt-1 text-xs text-emerald-600 dark:text-emerald-400 italic">
                        📝 {item.note}
                      </p>
                    )}
                  </td>
                  {/* Status */}
                  <td className="px-4 py-3">
                    {item.is_resolved ? (
                      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 text-xs font-medium">
                        <CheckCircle2 size={11} /> แก้ไขแล้ว
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-rose-100 dark:bg-rose-900/30 text-rose-700 dark:text-rose-400 text-xs font-medium">
                        <Clock size={11} /> ค้างอยู่
                      </span>
                    )}
                  </td>
                  {/* Actions */}
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      {!item.is_resolved && (
                        <button
                          onClick={() => setResolving(item)}
                          className="p-1.5 rounded-lg text-slate-400 hover:text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 transition-colors"
                          title="ทำเครื่องหมายว่าแก้ไขแล้ว"
                        >
                          <CheckCircle2 size={15} />
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(item.id)}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-900/20 transition-colors"
                        title="ลบ"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* ── Pagination ── */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-sm text-slate-500 dark:text-slate-400">
          <span>แสดง {page * LIMIT + 1}–{Math.min((page + 1) * LIMIT, total)} จาก {total} รายการ</span>
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

      {/* ── Resolve Modal ── */}
      {resolving && (
        <ResolveModal
          item={resolving}
          saving={saving}
          onClose={() => setResolving(null)}
          onResolve={handleResolve}
        />
      )}
    </div>
  );
}
