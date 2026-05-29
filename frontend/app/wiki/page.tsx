"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch, API_BASE } from "@/lib/api";
import { BookOpen, Download, Pencil, Trash2, X } from "lucide-react";

const DEFAULT_COMPANY = process.env.NEXT_PUBLIC_COMPANY_CODE || "DEVES";

// shared input / select classes
const inputCls = "rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-500 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500";

export default function WikiPage() {
  const [pages,       setPages]       = useState<any[]>([]);
  const [selected,    setSelected]    = useState<any>(null);
  const [search,      setSearch]      = useState("");
  const [company,     setCompany]     = useState(DEFAULT_COMPANY);
  const [loading,     setLoading]     = useState(false);
  const [deleting,    setDeleting]    = useState<string | null>(null);
  const [editing,     setEditing]     = useState(false);
  const [editContent, setEditContent] = useState("");
  const [exporting,   setExporting]   = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ company_code: company });
      if (search) params.set("q", search);
      const res  = await apiFetch(`${API_BASE}/api/wiki/pages?${params}`);
      const data = await res.json();
      setPages(data.items || []);
    } finally { setLoading(false); }
  }, [company, search]);

  useEffect(() => { load(); }, [load]);

  async function selectPage(page: any) {
    const res  = await apiFetch(`${API_BASE}/api/wiki/pages/${page.id}`);
    const data = await res.json();
    setSelected(data);
    setEditContent(data.content_markdown || "");
    setEditing(false);
  }

  async function deletePage(id: string) {
    if (!confirm("ต้องการลบ wiki page นี้?")) return;
    setDeleting(id);
    await apiFetch(`${API_BASE}/api/wiki/pages/${id}`, { method: "DELETE" });
    setDeleting(null);
    if (selected?.id === id) setSelected(null);
    load();
  }

  async function exportZip() {
    setExporting(true);
    try {
      const params = new URLSearchParams({ company_code: company });
      const res    = await apiFetch(`${API_BASE}/api/wiki/export?${params}`);
      if (!res.ok) { const err = await res.json().catch(() => ({ detail: "Export failed" })); alert(err.detail || "Export failed"); return; }
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement("a");
      const disposition = res.headers.get("Content-Disposition") || "";
      const match = disposition.match(/filename="([^"]+)"/);
      a.download = match ? match[1] : `wiki_${company}_export.zip`;
      a.href = url; a.click(); URL.revokeObjectURL(url);
    } finally { setExporting(false); }
  }

  async function saveEdit() {
    if (!selected) return;
    await apiFetch(`${API_BASE}/api/wiki/pages/${selected.id}`, {
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
      <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 p-5 shadow-sm flex flex-wrap items-center gap-4">
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
            <BookOpen size={22} className="text-blue-500" /> Wiki Pages
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            {pages.length} หน้า · สร้างโดย LLM จากแหล่งข้อมูล
          </p>
        </div>
        <div className="flex gap-2 items-center flex-wrap">
          <select value={company} onChange={(e) => { setCompany(e.target.value); setSelected(null); }} className={inputCls}>
            <option value="DEVES">DEVES</option>
            <option value="LOCKTON">LOCKTON</option>
          </select>
          <input value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder="🔍 ค้นหาชื่อหน้า…" className={inputCls + " w-48"} />
          <button
            onClick={exportZip}
            disabled={exporting || pages.length === 0}
            className="flex items-center gap-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {exporting
              ? <><span className="animate-spin">⏳</span> กำลัง Export…</>
              : <><Download size={14} /> Export ZIP</>}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Page list */}
        <div className="md:col-span-1 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
            รายการ ({pages.length})
          </div>
          {loading ? (
            <div className="p-8 text-center text-slate-400 dark:text-slate-600">กำลังโหลด…</div>
          ) : (
            <div className="overflow-y-auto" style={{ maxHeight: "70vh" }}>
              {pages.map((p) => (
                <div
                  key={p.id}
                  onClick={() => selectPage(p)}
                  className={`flex items-start gap-2 px-4 py-3 border-b border-slate-100 dark:border-slate-800/80
                              cursor-pointer transition-colors
                              hover:bg-indigo-50 dark:hover:bg-indigo-950/30 ${
                    selected?.id === p.id
                      ? "bg-indigo-50 dark:bg-indigo-950/30 border-l-2 border-l-indigo-500"
                      : ""
                  }`}
                >
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-slate-800 dark:text-slate-200 truncate">{p.title}</div>
                    <div className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">{p.slug} · v{p.version}</div>
                  </div>
                  <span className={`text-xs px-1.5 py-0.5 rounded-full shrink-0 font-medium ${
                    p.status === "published"
                      ? "bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-400"
                      : "bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-400"
                  }`}>
                    {p.status}
                  </span>
                </div>
              ))}
              {pages.length === 0 && (
                <div className="p-8 text-center text-slate-400 dark:text-slate-600 text-sm">ไม่พบหน้า wiki</div>
              )}
            </div>
          )}
        </div>

        {/* Page detail */}
        <div className="md:col-span-2 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm">
          {!selected ? (
            <div className="flex flex-col items-center justify-center h-full text-slate-400 dark:text-slate-600 text-sm p-20 gap-3">
              <BookOpen size={40} className="opacity-30" />
              <span>เลือกหน้า wiki เพื่อดูรายละเอียด</span>
            </div>
          ) : (
            <div className="flex flex-col h-full">
              <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex items-start justify-between gap-3">
                <div>
                  <h2 className="font-bold text-slate-800 dark:text-white text-lg">{selected.title}</h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    {selected.slug} · version {selected.version}
                    {selected.source_urls?.[0] && (
                      <> · <a href={selected.source_urls[0]} target="_blank" rel="noopener noreferrer"
                              className="text-indigo-500 hover:underline">source ↗</a></>
                    )}
                  </p>
                  {selected.summary && (
                    <p className="text-sm text-slate-600 dark:text-slate-400 mt-1 italic">{selected.summary}</p>
                  )}
                </div>
                <div className="flex gap-2 shrink-0">
                  <button
                    onClick={() => setEditing(!editing)}
                    className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition-colors"
                  >
                    {editing ? <><X size={12} /> ยกเลิก</> : <><Pencil size={12} /> แก้ไข</>}
                  </button>
                  <button
                    onClick={() => deletePage(selected.id)}
                    disabled={deleting === selected.id}
                    className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/30 text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-950/50 transition-colors"
                  >
                    <Trash2 size={12} /> ลบ
                  </button>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto p-4" style={{ maxHeight: "60vh" }}>
                {editing ? (
                  <div className="flex flex-col gap-3">
                    <textarea
                      value={editContent}
                      onChange={(e) => setEditContent(e.target.value)}
                      className="w-full h-96 rounded-xl border border-slate-200 dark:border-slate-700
                                 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200
                                 p-3 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                    <button
                      onClick={saveEdit}
                      className="self-start rounded-xl bg-indigo-600 hover:bg-indigo-700 px-4 py-2 text-sm text-white transition-colors"
                    >
                      💾 บันทึก
                    </button>
                  </div>
                ) : (
                  <pre className="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap font-sans leading-relaxed">
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
