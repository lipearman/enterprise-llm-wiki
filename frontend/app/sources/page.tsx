"use client";

import { useState, useEffect, useCallback } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8080";
const DEFAULT_COMPANY = process.env.NEXT_PUBLIC_COMPANY_CODE || "DEVES";

type CrawlerBackend = "trafilatura" | "playwright" | "crawl4ai";

const CRAWLER_INFO: Record<CrawlerBackend, { icon: string; label: string; desc: string; badge: string }> = {
  trafilatura: {
    icon: "⚡",
    label: "Trafilatura",
    desc: "เร็ว, ไม่ใช้ browser — เหมาะกับเว็บ HTML ทั่วไป",
    badge: "bg-green-100 text-green-700",
  },
  playwright: {
    icon: "🎭",
    label: "Playwright",
    desc: "Headless Chromium — render JavaScript ได้",
    badge: "bg-blue-100 text-blue-700",
  },
  crawl4ai: {
    icon: "🤖",
    label: "crawl4ai",
    desc: "LLM-aware, Markdown คุณภาพสูงสุด + JS rendering",
    badge: "bg-violet-100 text-violet-700",
  },
};

export default function SourcesPage() {
  const [sources, setSources] = useState<any[]>([]);
  const [company, setCompany] = useState(DEFAULT_COMPANY);
  const [loading, setLoading] = useState(false);

  // Add URL form
  const [url, setUrl] = useState("");
  const [addingUrl, setAddingUrl] = useState(false);
  const [crawler, setCrawler] = useState<CrawlerBackend>("trafilatura");
  const [deepEnrich, setDeepEnrich] = useState(true);
  const [jobResult, setJobResult] = useState<any>(null);

  // File upload form
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  // Backend info from server
  const [backendInfo, setBackendInfo] = useState<any>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [srcRes, beRes] = await Promise.all([
        fetch(`${API_BASE}/api/sources?company_code=${company}`),
        fetch(`${API_BASE}/api/sources/backends`),
      ]);
      const srcData = await srcRes.json();
      const beData = await beRes.json();
      setSources(srcData.items || []);
      setBackendInfo(beData);
      // Sync crawler selector with server default
      if (beData.default && !url) setCrawler(beData.default as CrawlerBackend);
    } finally {
      setLoading(false);
    }
  }, [company]);

  useEffect(() => { load(); }, [load]);

  async function addUrl() {
    if (!url.trim()) return;
    setAddingUrl(true); setJobResult(null);
    try {
      const res = await fetch(`${API_BASE}/api/sources/url`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url,
          company_code: company,
          run_deep_enrichment: deepEnrich,
          crawler_backend: crawler,
        }),
      });
      const data = await res.json();
      setJobResult(data); setUrl(""); load();
    } finally { setAddingUrl(false); }
  }

  async function uploadFileHandler() {
    if (!uploadFile) return;
    setUploading(true); setJobResult(null);
    try {
      const form = new FormData();
      form.append("file", uploadFile);
      form.append("company_code", company);
      form.append("run_deep_enrichment", String(deepEnrich));
      const res = await fetch(`${API_BASE}/api/sources/file`, { method: "POST", body: form });
      const data = await res.json();
      setJobResult(data); setUploadFile(null); load();
    } finally { setUploading(false); }
  }

  async function deactivate(id: string) {
    if (!confirm("ปิดใช้งาน source นี้?")) return;
    await fetch(`${API_BASE}/api/sources/${id}`, { method: "DELETE" });
    load();
  }

  const typeIcon: Record<string, string> = { url: "🌐", file: "📄" };

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="rounded-2xl bg-white p-5 shadow-sm flex flex-wrap items-center gap-4">
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-slate-800">🔗 Sources</h1>
          <p className="text-sm text-slate-500 mt-0.5">{sources.length} แหล่งข้อมูล · URL และไฟล์</p>
        </div>
        <select value={company} onChange={(e) => setCompany(e.target.value)} className="rounded-lg border px-3 py-1.5 text-sm">
          <option value="DEVES">DEVES</option>
          <option value="LOCKTON">LOCKTON</option>
        </select>
      </div>

      {/* Crawler backend selector */}
      <div className="rounded-2xl bg-white p-5 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <h2 className="font-semibold text-slate-700">🕷️ Crawler Backend</h2>
          {backendInfo && (
            <span className="text-xs text-slate-400">
              (default จาก .env: <code className="bg-slate-100 px-1 rounded">{backendInfo.default}</code>)
            </span>
          )}
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {(Object.keys(CRAWLER_INFO) as CrawlerBackend[]).map((b) => {
            const info = CRAWLER_INFO[b];
            const selected = crawler === b;
            return (
              <button
                key={b}
                onClick={() => setCrawler(b)}
                className={`text-left rounded-xl border-2 p-3 transition-all ${
                  selected
                    ? "border-blue-500 bg-blue-50"
                    : "border-slate-200 hover:border-slate-300 hover:bg-slate-50"
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-lg">{info.icon}</span>
                  <span className="font-semibold text-sm text-slate-800">{info.label}</span>
                  {selected && <span className="ml-auto text-xs px-1.5 py-0.5 bg-blue-500 text-white rounded-full">เลือก</span>}
                </div>
                <p className="text-xs text-slate-500">{info.desc}</p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Add URL + Upload file */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="rounded-2xl bg-white p-5 shadow-sm">
          <h2 className="font-semibold text-slate-700 mb-3">➕ เพิ่ม URL</h2>
          <div className="flex flex-col gap-2">
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && addUrl()}
              placeholder="https://example.com/page"
              className="rounded-xl border px-3 py-2 text-sm"
            />

            {/* Selected crawler badge */}
            <div className="flex items-center gap-2">
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${CRAWLER_INFO[crawler].badge}`}>
                {CRAWLER_INFO[crawler].icon} {CRAWLER_INFO[crawler].label}
              </span>
              <span className="text-xs text-slate-400">จะใช้ crawler นี้</span>
            </div>

            <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
              <input type="checkbox" checked={deepEnrich} onChange={(e) => setDeepEnrich(e.target.checked)} className="rounded" />
              Deep Enrichment (Wiki + QA + Relationships)
            </label>
            <button
              onClick={addUrl}
              disabled={addingUrl || !url.trim()}
              className="rounded-xl bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {addingUrl ? "กำลังสร้าง job…" : `🚀 Ingest URL`}
            </button>
          </div>
        </div>

        <div className="rounded-2xl bg-white p-5 shadow-sm">
          <h2 className="font-semibold text-slate-700 mb-3">📤 อัพโหลดไฟล์</h2>
          <div className="flex flex-col gap-2">
            <input
              type="file"
              accept=".pdf,.docx,.xlsx,.xlsm,.txt,.md"
              onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
              className="rounded-xl border px-3 py-2 text-sm"
            />
            <p className="text-xs text-slate-400">รองรับ: PDF, DOCX, XLSX, TXT, MD</p>
            <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
              <input type="checkbox" checked={deepEnrich} onChange={(e) => setDeepEnrich(e.target.checked)} className="rounded" />
              Deep Enrichment (Wiki + QA + Relationships)
            </label>
            <button
              onClick={uploadFileHandler}
              disabled={uploading || !uploadFile}
              className="rounded-xl bg-slate-800 px-4 py-2 text-sm text-white hover:bg-slate-700 disabled:opacity-50"
            >
              {uploading ? "กำลังอัพโหลด…" : "📤 Upload & Ingest"}
            </button>
          </div>
        </div>
      </div>

      {/* Job result */}
      {jobResult && (
        <div className="rounded-2xl bg-green-50 border border-green-200 p-4">
          <p className="text-sm font-semibold text-green-700">✅ Job สร้างแล้ว</p>
          <pre className="text-xs text-green-600 mt-1">{JSON.stringify(jobResult, null, 2)}</pre>
        </div>
      )}

      {/* Sources list */}
      <div className="rounded-2xl bg-white shadow-sm overflow-hidden">
        <div className="p-3 border-b bg-slate-50 text-xs font-semibold text-slate-500 uppercase tracking-wide">
          แหล่งข้อมูลทั้งหมด ({sources.length})
        </div>
        {loading ? (
          <div className="p-10 text-center text-slate-400">กำลังโหลด…</div>
        ) : (
          <div>
            {sources.map((src) => (
              <div
                key={src.id}
                className={`flex items-center gap-3 px-4 py-3 border-b hover:bg-slate-50 ${!src.is_active ? "opacity-40" : ""}`}
              >
                <span className="text-xl">{typeIcon[src.source_type] || "📦"}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-800 truncate">{src.source_name || src.source_url}</p>
                  {src.source_url && src.source_name && (
                    <a
                      href={src.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-blue-500 hover:underline truncate block"
                    >
                      {src.source_url}
                    </a>
                  )}
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full ${src.is_active ? "bg-green-100 text-green-700" : "bg-slate-100 text-slate-500"}`}>
                  {src.is_active ? "active" : "inactive"}
                </span>
                <button
                  onClick={() => deactivate(src.id)}
                  disabled={!src.is_active}
                  className="text-xs px-2 py-1 rounded-lg border border-red-200 text-red-500 hover:bg-red-50 disabled:opacity-30"
                >
                  ปิด
                </button>
              </div>
            ))}
            {sources.length === 0 && (
              <div className="p-10 text-center text-slate-400 text-sm">ยังไม่มีแหล่งข้อมูล</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
