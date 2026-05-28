"use client";

import { useState, useEffect, useCallback } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8080";
const DEFAULT_COMPANY = process.env.NEXT_PUBLIC_COMPANY_CODE || "DEVES";

export default function QAPage() {
  const [items, setItems] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [company, setCompany] = useState(DEFAULT_COMPANY);
  const [loading, setLoading] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [editQ, setEditQ] = useState("");
  const [editA, setEditA] = useState("");
  const [saving, setSaving] = useState(false);
  const [newQ, setNewQ] = useState("");
  const [newA, setNewA] = useState("");
  const [creating, setCreating] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [offset, setOffset] = useState(0);
  const LIMIT = 30;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ company_code: company, limit: String(LIMIT), offset: String(offset) });
      if (search) params.set("q", search);
      const res = await fetch(`${API_BASE}/api/wiki/qa?${params}`);
      const data = await res.json();
      setItems(data.items || []);
    } finally {
      setLoading(false);
    }
  }, [company, search, offset]);

  useEffect(() => { setOffset(0); }, [company, search]);
  useEffect(() => { load(); }, [load]);

  function startEdit(item: any) {
    setEditId(item.id);
    setEditQ(item.question);
    setEditA(item.answer);
  }

  async function saveEdit(id: string) {
    setSaving(true);
    await fetch(`${API_BASE}/api/wiki/qa/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: editQ, answer: editA }),
    });
    setSaving(false);
    setEditId(null);
    load();
  }

  async function deleteQA(id: string) {
    if (!confirm("ต้องการลบ QA นี้?")) return;
    await fetch(`${API_BASE}/api/wiki/qa/${id}`, { method: "DELETE" });
    load();
  }

  async function toggleActive(item: any) {
    await fetch(`${API_BASE}/api/wiki/qa/${item.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_active: !item.is_active }),
    });
    load();
  }

  async function createQA() {
    if (!newQ.trim() || !newA.trim()) return;
    setCreating(true);
    await fetch(`${API_BASE}/api/wiki/qa`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ company_code: company, question: newQ, answer: newA }),
    });
    setCreating(false);
    setNewQ(""); setNewA(""); setShowCreate(false);
    load();
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-2xl bg-white p-5 shadow-sm flex flex-wrap items-center gap-4">
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-slate-800">❓ QA Editor</h1>
          <p className="text-sm text-slate-500 mt-0.5">{items.length} รายการ · Canonical QA สำหรับ retrieval</p>
        </div>
        <div className="flex gap-2 flex-wrap items-center">
          <select value={company} onChange={(e) => setCompany(e.target.value)} className="rounded-lg border px-3 py-1.5 text-sm">
            <option value="DEVES">DEVES</option>
            <option value="LOCKTON">LOCKTON</option>
          </select>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="🔍 ค้นหาคำถาม…"
            className="rounded-lg border px-3 py-1.5 text-sm w-48"
          />
          <button onClick={() => setShowCreate(!showCreate)} className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700">
            ＋ เพิ่ม QA
          </button>
        </div>
      </div>

      {/* Create form */}
      {showCreate && (
        <div className="rounded-2xl bg-white p-5 shadow-sm border-l-4 border-blue-500">
          <h3 className="font-semibold text-slate-700 mb-3">➕ สร้าง QA ใหม่</h3>
          <div className="flex flex-col gap-3">
            <input value={newQ} onChange={(e) => setNewQ(e.target.value)} placeholder="คำถาม…" className="rounded-xl border px-3 py-2 text-sm" />
            <textarea value={newA} onChange={(e) => setNewA(e.target.value)} rows={3} placeholder="คำตอบ…" className="rounded-xl border px-3 py-2 text-sm" />
            <div className="flex gap-2">
              <button onClick={createQA} disabled={creating || !newQ.trim() || !newA.trim()} className="rounded-xl bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50">
                {creating ? "กำลังสร้าง…" : "💾 บันทึก"}
              </button>
              <button onClick={() => setShowCreate(false)} className="rounded-xl border px-4 py-2 text-sm hover:bg-slate-50">ยกเลิก</button>
            </div>
          </div>
        </div>
      )}

      {/* QA list */}
      <div className="rounded-2xl bg-white shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-slate-400">กำลังโหลด…</div>
        ) : items.length === 0 ? (
          <div className="p-12 text-center text-slate-400 text-sm">ไม่พบ QA</div>
        ) : (
          <div>
            {items.map((item, i) => (
              <div key={item.id} className={`border-b p-4 ${!item.is_active ? "opacity-50" : ""}`}>
                {editId === item.id ? (
                  <div className="flex flex-col gap-2">
                    <input value={editQ} onChange={(e) => setEditQ(e.target.value)} className="rounded-xl border px-3 py-2 text-sm font-medium" />
                    <textarea value={editA} onChange={(e) => setEditA(e.target.value)} rows={3} className="rounded-xl border px-3 py-2 text-sm" />
                    <div className="flex gap-2">
                      <button onClick={() => saveEdit(item.id)} disabled={saving} className="rounded-xl bg-blue-600 px-3 py-1.5 text-xs text-white hover:bg-blue-700 disabled:opacity-50">
                        {saving ? "กำลังบันทึก…" : "💾 บันทึก"}
                      </button>
                      <button onClick={() => setEditId(null)} className="rounded-xl border px-3 py-1.5 text-xs hover:bg-slate-50">ยกเลิก</button>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-start gap-3">
                    <span className="text-slate-300 text-xs mt-1 w-6 text-right shrink-0">{offset + i + 1}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-slate-800">{item.question}</p>
                      <p className="text-sm text-slate-600 mt-1 whitespace-pre-wrap">{item.answer}</p>
                    </div>
                    <div className="flex gap-1 shrink-0">
                      <button onClick={() => toggleActive(item)} title={item.is_active ? "ปิดใช้งาน" : "เปิดใช้งาน"} className="text-xs px-2 py-1 rounded-lg border hover:bg-slate-50">
                        {item.is_active ? "✅" : "⭕"}
                      </button>
                      <button onClick={() => startEdit(item)} className="text-xs px-2 py-1 rounded-lg border hover:bg-slate-50">✏️</button>
                      <button onClick={() => deleteQA(item.id)} className="text-xs px-2 py-1 rounded-lg border border-red-200 text-red-600 hover:bg-red-50">🗑️</button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Pagination */}
      <div className="flex justify-center gap-2">
        <button onClick={() => setOffset(Math.max(0, offset - LIMIT))} disabled={offset === 0} className="px-3 py-1.5 rounded-lg border text-sm disabled:opacity-40 hover:bg-slate-50">
          ← ก่อนหน้า
        </button>
        <span className="px-3 py-1.5 text-sm text-slate-500">หน้า {Math.floor(offset / LIMIT) + 1}</span>
        <button onClick={() => setOffset(offset + LIMIT)} disabled={items.length < LIMIT} className="px-3 py-1.5 rounded-lg border text-sm disabled:opacity-40 hover:bg-slate-50">
          ถัดไป →
        </button>
      </div>
    </div>
  );
}
