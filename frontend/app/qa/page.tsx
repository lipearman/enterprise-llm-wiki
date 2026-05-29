"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch, API_BASE } from "@/lib/api";
import { HelpCircle, Plus, Pencil, Trash2, X, ChevronLeft, ChevronRight, Save } from "lucide-react";

const DEFAULT_COMPANY = process.env.NEXT_PUBLIC_COMPANY_CODE || "DEVES";
const LIMIT = 30;

const inputCls = "rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-500 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500";

// ── Edit Modal ────────────────────────────────────────────────────────────────
function EditModal({
  item,
  saving,
  onClose,
  onSave,
}: {
  item: any;
  saving: boolean;
  onClose: () => void;
  onSave: (id: string, q: string, a: string) => void;
}) {
  const [q, setQ] = useState(item.question);
  const [a, setA] = useState(item.answer);

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 dark:bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal card */}
      <div className="relative w-full max-w-xl bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 z-10 flex flex-col">

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 dark:border-slate-800">
          <h3 className="font-semibold text-slate-800 dark:text-white flex items-center gap-2 text-base">
            <span className="w-6 h-6 rounded-lg bg-indigo-100 dark:bg-indigo-950/60 flex items-center justify-center">
              <Pencil size={13} className="text-indigo-500" />
            </span>
            แก้ไข QA
          </h3>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 flex flex-col gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1.5 uppercase tracking-wide">
              คำถาม
            </label>
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              className={inputCls + " w-full font-medium"}
              placeholder="คำถาม…"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1.5 uppercase tracking-wide">
              คำตอบ
            </label>
            <textarea
              value={a}
              onChange={(e) => setA(e.target.value)}
              rows={6}
              className={inputCls + " w-full resize-y"}
              placeholder="คำตอบ…"
            />
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 px-5 py-4 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 rounded-b-2xl">
          <button
            onClick={onClose}
            className="rounded-xl border border-slate-200 dark:border-slate-700 px-4 py-2 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
          >
            ยกเลิก
          </button>
          <button
            onClick={() => onSave(item.id, q, a)}
            disabled={saving || !q.trim() || !a.trim()}
            className="flex items-center gap-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 px-4 py-2 text-sm text-white disabled:opacity-50 transition-colors shadow-sm shadow-indigo-600/20"
          >
            <Save size={14} />
            {saving ? "กำลังบันทึก…" : "บันทึก"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function QAPage() {
  const [items,      setItems]      = useState<any[]>([]);
  const [search,     setSearch]     = useState("");
  const [company,    setCompany]    = useState(DEFAULT_COMPANY);
  const [loading,    setLoading]    = useState(false);
  const [editItem,   setEditItem]   = useState<any>(null);   // item being edited in modal
  const [saving,     setSaving]     = useState(false);
  const [newQ,       setNewQ]       = useState("");
  const [newA,       setNewA]       = useState("");
  const [creating,   setCreating]   = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [offset,     setOffset]     = useState(0);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ company_code: company, limit: String(LIMIT), offset: String(offset) });
      if (search) params.set("q", search);
      const res  = await apiFetch(`${API_BASE}/api/wiki/qa?${params}`);
      const data = await res.json();
      setItems(data.items || []);
    } finally { setLoading(false); }
  }, [company, search, offset]);

  useEffect(() => { setOffset(0); }, [company, search]);
  useEffect(() => { load(); }, [load]);

  async function saveEdit(id: string, q: string, a: string) {
    setSaving(true);
    await apiFetch(`${API_BASE}/api/wiki/qa/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q, answer: a }),
    });
    setSaving(false);
    setEditItem(null);
    load();
  }

  async function deleteQA(id: string) {
    if (!confirm("ต้องการลบ QA นี้?")) return;
    await apiFetch(`${API_BASE}/api/wiki/qa/${id}`, { method: "DELETE" });
    load();
  }

  async function toggleActive(item: any) {
    await apiFetch(`${API_BASE}/api/wiki/qa/${item.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_active: !item.is_active }),
    });
    load();
  }

  async function createQA() {
    if (!newQ.trim() || !newA.trim()) return;
    setCreating(true);
    await apiFetch(`${API_BASE}/api/wiki/qa`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ company_code: company, question: newQ, answer: newA }),
    });
    setCreating(false); setNewQ(""); setNewA(""); setShowCreate(false); load();
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Edit Modal */}
      {editItem && (
        <EditModal
          item={editItem}
          saving={saving}
          onClose={() => setEditItem(null)}
          onSave={saveEdit}
        />
      )}

      {/* Header */}
      <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 p-5 shadow-sm flex flex-wrap items-center gap-4">
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
            <HelpCircle size={22} className="text-violet-500" /> QA Editor
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            {items.length} รายการ · Canonical QA สำหรับ retrieval
          </p>
        </div>
        <div className="flex gap-2 flex-wrap items-center">
          <select
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="DEVES">DEVES</option>
            <option value="LOCKTON">LOCKTON</option>
          </select>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="🔍 ค้นหาคำถาม…"
            className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-500 px-3 py-1.5 text-sm w-48 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="flex items-center gap-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 px-3 py-1.5 text-sm font-medium text-white transition-colors shadow-sm shadow-indigo-600/20"
          >
            <Plus size={15} /> เพิ่ม QA
          </button>
        </div>
      </div>

      {/* Create form */}
      {showCreate && (
        <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 p-5 shadow-sm border-l-4 border-l-indigo-500">
          <h3 className="font-semibold text-slate-700 dark:text-slate-200 mb-3 flex items-center gap-2">
            <Plus size={16} className="text-indigo-500" /> สร้าง QA ใหม่
          </h3>
          <div className="flex flex-col gap-3">
            <input value={newQ} onChange={(e) => setNewQ(e.target.value)} placeholder="คำถาม…" className={inputCls} />
            <textarea value={newA} onChange={(e) => setNewA(e.target.value)} rows={3} placeholder="คำตอบ…" className={inputCls} />
            <div className="flex gap-2">
              <button
                onClick={createQA}
                disabled={creating || !newQ.trim() || !newA.trim()}
                className="rounded-xl bg-indigo-600 hover:bg-indigo-700 px-4 py-2 text-sm text-white disabled:opacity-50 transition-colors"
              >
                {creating ? "กำลังสร้าง…" : "💾 บันทึก"}
              </button>
              <button
                onClick={() => setShowCreate(false)}
                className="rounded-xl border border-slate-200 dark:border-slate-700 px-4 py-2 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
              >
                ยกเลิก
              </button>
            </div>
          </div>
        </div>
      )}

      {/* QA list */}
      <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-slate-400 dark:text-slate-600">กำลังโหลด…</div>
        ) : items.length === 0 ? (
          <div className="p-12 text-center text-slate-400 dark:text-slate-600 text-sm">ไม่พบ QA</div>
        ) : (
          <div>
            {items.map((item, i) => (
              <div
                key={item.id}
                className={`flex items-start gap-3 border-b border-slate-100 dark:border-slate-800/80 px-4 py-3.5 transition-opacity hover:bg-slate-50 dark:hover:bg-slate-800/40 ${!item.is_active ? "opacity-40" : ""}`}
              >
                {/* Row number */}
                <span className="text-slate-300 dark:text-slate-600 text-xs mt-1 w-6 text-right shrink-0 font-mono">
                  {offset + i + 1}
                </span>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">{item.question}</p>
                  <p className="text-sm text-slate-600 dark:text-slate-400 mt-1 whitespace-pre-wrap">{item.answer}</p>
                </div>

                {/* Actions */}
                <div className="flex gap-1 shrink-0">
                  <button
                    onClick={() => toggleActive(item)}
                    title={item.is_active ? "ปิดใช้งาน" : "เปิดใช้งาน"}
                    className="text-xs px-2 py-1 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                  >
                    {item.is_active ? "✅" : "⭕"}
                  </button>
                  <button
                    onClick={() => setEditItem(item)}
                    title="แก้ไข"
                    className="flex items-center gap-1 text-xs px-2 py-1 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 hover:border-indigo-300 dark:hover:border-indigo-800 text-slate-600 dark:text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
                  >
                    <Pencil size={11} />
                  </button>
                  <button
                    onClick={() => deleteQA(item.id)}
                    title="ลบ"
                    className="flex items-center gap-1 text-xs px-2 py-1 rounded-lg border border-red-200 dark:border-red-900 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors"
                  >
                    <Trash2 size={11} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Pagination */}
      <div className="flex justify-center items-center gap-3">
        <button
          onClick={() => setOffset(Math.max(0, offset - LIMIT))}
          disabled={offset === 0}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-sm text-slate-600 dark:text-slate-400 disabled:opacity-40 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
        >
          <ChevronLeft size={14} /> ก่อนหน้า
        </button>
        <span className="px-3 py-1.5 text-sm text-slate-500 dark:text-slate-400">
          หน้า {Math.floor(offset / LIMIT) + 1}
        </span>
        <button
          onClick={() => setOffset(offset + LIMIT)}
          disabled={items.length < LIMIT}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-sm text-slate-600 dark:text-slate-400 disabled:opacity-40 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
        >
          ถัดไป <ChevronRight size={14} />
        </button>
      </div>
    </div>
  );
}
