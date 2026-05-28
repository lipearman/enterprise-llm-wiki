"use client";

import { useState, useEffect, useCallback } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8080";
const DEFAULT_COMPANY = process.env.NEXT_PUBLIC_COMPANY_CODE || "DEVES";

export default function WikiPage() {
  const [pages, setPages] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [search, setSearch] = useState("");
  const [company, setCompany] = useState(DEFAULT_COMPANY);
  const [loading, setLoading] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ company_code: company });
      if (search) params.set("q", search);
      const res = await fetch(`${API_BASE}/api/wiki/pages?${params}`);
      const data = await res.json();
      setPages(data.items || []);
    } finally {
      setLoading(false);
    }
  }, [company, search]);

  useEffect(() => { load(); }, [load]);

  async function selectPage(page: any) {
    const res = await fetch(`${API_BASE}/api/wiki/pages/${page.id}`);
    const data = await res.json();
    setSelected(data);
    setEditContent(data.content_markdown || "");
    setEditing(false);
  }

  async function deletePage(id: string) {
    if (!confirm("ต้องการลบ wiki page นี้?")) return;
    setDeleting(id);
    await fetch(`${API_BASE}/api/wiki/pages/${id}`, { method: "DELETE" });
    setDeleting(null);
    if (selected?.id === id) setSelected(null);
    load();
  }

  async function saveEdit() {
    if (!selected) return;
    await fetch(`${API_BASE}/api/wiki/pages/${selected.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content_markdown: editContent }),
    });
    setEditing(false);
    selectPage(selected);
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="rounded-2xl bg-white p-5 shadow-sm flex flex-wrap items-center gap-4">
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-slate-800">📖 Wiki Pages</h1>
          <p className="text-sm text-slate-500 mt-0.5">{pages.length} หน้า · สร้างโดย LLM จากแหล่งข้อมูล</p>
        </div>
        <div className="flex gap-2 items-center">
          <select value={company} onChange={(e) => { setCompany(e.target.value); setSelected(null); }} className="rounded-lg border px-3 py-1.5 text-sm">
            <option value="DEVES">DEVES</option>
            <option value="LOCKTON">LOCKTON</option>
          </select>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="🔍 ค้นหาชื่อหน้า…"
            className="rounded-lg border px-3 py-1.5 text-sm w-48"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Page list */}
        <div className="md:col-span-1 rounded-2xl bg-white shadow-sm overflow-hidden">
          <div className="p-3 border-b bg-slate-50 text-xs font-semibold text-slate-500 uppercase tracking-wide">
            รายการ ({pages.length})
          </div>
          {loading ? (
            <div className="p-8 text-center text-slate-400">กำลังโหลด…</div>
          ) : (
            <div className="overflow-y-auto" style={{ maxHeight: "70vh" }}>
              {pages.map((p) => (
                <div
                  key={p.id}
                  onClick={() => selectPage(p)}
                  className={`flex items-start gap-2 px-4 py-3 border-b cursor-pointer hover:bg-blue-50 transition-colors ${
                    selected?.id === p.id ? "bg-blue-50 border-l-2 border-l-blue-500" : ""
                  }`}
                >
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-slate-800 truncate">{p.title}</div>
                    <div className="text-xs text-slate-400 mt-0.5">{p.slug} · v{p.version}</div>
                  </div>
                  <span className={`text-xs px-1.5 py-0.5 rounded-full shrink-0 ${p.status === "published" ? "bg-green-100 text-green-700" : "bg-yellow-100 text-yellow-700"}`}>
                    {p.status}
                  </span>
                </div>
              ))}
              {pages.length === 0 && (
                <div className="p-8 text-center text-slate-400 text-sm">ไม่พบหน้า wiki</div>
              )}
            </div>
          )}
        </div>

        {/* Page detail */}
        <div className="md:col-span-2 rounded-2xl bg-white shadow-sm">
          {!selected ? (
            <div className="flex items-center justify-center h-full text-slate-400 text-sm p-20">
              👈 เลือกหน้า wiki เพื่อดูรายละเอียด
            </div>
          ) : (
            <div className="flex flex-col h-full">
              <div className="p-4 border-b flex items-start justify-between gap-3">
                <div>
                  <h2 className="font-bold text-slate-800 text-lg">{selected.title}</h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {selected.slug} · version {selected.version} ·{" "}
                    {selected.source_urls?.[0] && (
                      <a href={selected.source_urls[0]} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">
                        source ↗
                      </a>
                    )}
                  </p>
                  {selected.summary && <p className="text-sm text-slate-600 mt-1 italic">{selected.summary}</p>}
                </div>
                <div className="flex gap-2 shrink-0">
                  <button onClick={() => setEditing(!editing)} className="text-xs px-3 py-1.5 rounded-lg border hover:bg-slate-50">
                    {editing ? "ยกเลิก" : "✏️ แก้ไข"}
                  </button>
                  <button
                    onClick={() => deletePage(selected.id)}
                    disabled={deleting === selected.id}
                    className="text-xs px-3 py-1.5 rounded-lg bg-red-50 text-red-600 hover:bg-red-100 border border-red-200"
                  >
                    🗑️ ลบ
                  </button>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto p-4" style={{ maxHeight: "60vh" }}>
                {editing ? (
                  <div className="flex flex-col gap-3">
                    <textarea
                      value={editContent}
                      onChange={(e) => setEditContent(e.target.value)}
                      className="w-full h-96 rounded-xl border p-3 text-sm font-mono"
                    />
                    <button onClick={saveEdit} className="self-start rounded-xl bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700">
                      💾 บันทึก
                    </button>
                  </div>
                ) : (
                  <pre className="text-sm text-slate-700 whitespace-pre-wrap font-sans leading-relaxed">
                    {selected.content_markdown}
                  </pre>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
