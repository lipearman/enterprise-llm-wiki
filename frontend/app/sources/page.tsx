"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch, API_BASE } from "@/lib/api";
import { Link2, Globe, FileText, Rocket, Upload, PowerOff } from "lucide-react";

const DEFAULT_COMPANY = process.env.NEXT_PUBLIC_COMPANY_CODE || "DEVES";

type CrawlerBackend = "trafilatura" | "playwright" | "crawl4ai";

const CRAWLER_INFO: Record<CrawlerBackend, { icon: string; label: string; desc: string; badge: string }> = {
  trafilatura: {
    icon: "⚡",
    label: "Trafilatura",
    desc: "เร็ว, ไม่ใช้ browser — เหมาะกับเว็บ HTML ทั่วไป",
    badge: "bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-400",
  },
  playwright: {
    icon: "🎭",
    label: "Playwright",
    desc: "Headless Chromium — render JavaScript ได้",
    badge: "bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-400",
  },
  crawl4ai: {
    icon: "🤖",
    label: "crawl4ai",
    desc: "LLM-aware, Markdown คุณภาพสูงสุด + JS rendering",
    badge: "bg-violet-100 dark:bg-violet-900/40 text-violet-700 dark:text-violet-400",
  },
};

const inputCls = "rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-500 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500";

export default function SourcesPage() {
  const [sources,     setSources]     = useState<any[]>([]);
  const [company,     setCompany]     = useState(DEFAULT_COMPANY);
  const [loading,     setLoading]     = useState(false);
  const [url,         setUrl]         = useState("");
  const [addingUrl,   setAddingUrl]   = useState(false);
  const [crawler,     setCrawler]     = useState<CrawlerBackend>("trafilatura");
  const [deepEnrich,  setDeepEnrich]  = useState(true);
  const [jobResult,   setJobResult]   = useState<any>(null);
  const [uploadFile,  setUploadFile]  = useState<File | null>(null);
  const [uploading,   setUploading]   = useState(false);
  const [backendInfo, setBackendInfo] = useState<any>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [srcRes, beRes] = await Promise.all([
        apiFetch(`${API_BASE}/api/sources?company_code=${company}`),
        apiFetch(`${API_BASE}/api/sources/backends`),
      ]);
      const srcData = await srcRes.json();
      const beData  = await beRes.json();
      setSources(srcData.items || []);
      setBackendInfo(beData);
      if (beData.default && !url) setCrawler(beData.default as CrawlerBackend);
    } finally { setLoading(false); }
  }, [company]);

  useEffect(() => { load(); }, [load]);

  async function addUrl() {
    if (!url.trim()) return;
    setAddingUrl(true); setJobResult(null);
    try {
      const res  = await apiFetch(`${API_BASE}/api/sources/url`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, company_code: company, run_deep_enrichment: deepEnrich, crawler_backend: crawler }),
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
      const res  = await apiFetch(`${API_BASE}/api/sources/file`, { method: "POST", body: form });
      const data = await res.json();
      setJobResult(data); setUploadFile(null); load();
    } finally { setUploading(false); }
  }

  async function deactivate(id: string) {
    if (!confirm("ปิดใช้งาน source นี้?")) return;
    await apiFetch(`${API_BASE}/api/sources/${id}`, { method: "DELETE" });
    load();
  }

  const typeIcon: Record<string, React.ReactNode> = {
    url:  <Globe size={16} className="text-blue-500" />,
    file: <FileText size={16} className="text-amber-500" />,
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 p-5 shadow-sm flex flex-wrap items-center gap-4">
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
            <Link2 size={22} className="text-amber-500" /> Sources
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            {sources.length} แหล่งข้อมูล · URL และไฟล์
          </p>
        </div>
        <select
          value={company}
          onChange={(e) => setCompany(e.target.value)}
          className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="DEVES">DEVES</option>
          <option value="LOCKTON">LOCKTON</option>
        </select>
      </div>

      {/* Crawler backend selector */}
      <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 p-5 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <h2 className="font-semibold text-slate-700 dark:text-slate-200">🕷️ Crawler Backend</h2>
          {backendInfo && (
            <span className="text-xs text-slate-400 dark:text-slate-500">
              (default: <code className="bg-slate-100 dark:bg-slate-800 px-1 rounded">{backendInfo.default}</code>)
            </span>
          )}
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {(Object.keys(CRAWLER_INFO) as CrawlerBackend[]).map((b) => {
            const info = CRAWLER_INFO[b];
            const sel  = crawler === b;
            return (
              <button key={b} onClick={() => setCrawler(b)}
                className={`text-left rounded-xl border-2 p-3 transition-all ${
                  sel
                    ? "border-indigo-500 bg-indigo-50 dark:bg-indigo-950/30"
                    : "border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800/50"
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-lg">{info.icon}</span>
                  <span className="font-semibold text-sm text-slate-800 dark:text-slate-200">{info.label}</span>
                  {sel && (
                    <span className="ml-auto text-xs px-1.5 py-0.5 bg-indigo-600 text-white rounded-full">เลือก</span>
                  )}
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400">{info.desc}</p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Add URL + Upload file */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 p-5 shadow-sm">
          <h2 className="font-semibold text-slate-700 dark:text-slate-200 mb-3 flex items-center gap-2">
            <Globe size={16} className="text-blue-500" /> เพิ่ม URL
          </h2>
          <div className="flex flex-col gap-2">
            <input value={url} onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && addUrl()}
              placeholder="https://example.com/page" className={inputCls} />
            <div className="flex items-center gap-2">
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${CRAWLER_INFO[crawler].badge}`}>
                {CRAWLER_INFO[crawler].icon} {CRAWLER_INFO[crawler].label}
              </span>
              <span className="text-xs text-slate-400 dark:text-slate-500">จะใช้ crawler นี้</span>
            </div>
            <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400 cursor-pointer select-none">
              <input type="checkbox" checked={deepEnrich} onChange={(e) => setDeepEnrich(e.target.checked)} className="rounded accent-indigo-600" />
              Deep Enrichment (Wiki + QA + Relationships)
            </label>
            <button onClick={addUrl} disabled={addingUrl || !url.trim()}
              className="flex items-center justify-center gap-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 px-4 py-2 text-sm text-white disabled:opacity-50 transition-colors shadow-sm shadow-indigo-600/20">
              <Rocket size={14} />
              {addingUrl ? "กำลังสร้าง job…" : "Ingest URL"}
            </button>
          </div>
        </div>

        <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 p-5 shadow-sm">
          <h2 className="font-semibold text-slate-700 dark:text-slate-200 mb-3 flex items-center gap-2">
            <Upload size={16} className="text-violet-500" /> อัพโหลดไฟล์
          </h2>
          <div className="flex flex-col gap-2">
            <input type="file" accept=".pdf,.docx,.xlsx,.xlsm,.txt,.md"
              onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
              className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 px-3 py-2 text-sm file:mr-2 file:rounded-lg file:border-0 file:bg-indigo-50 dark:file:bg-indigo-950 file:text-indigo-700 dark:file:text-indigo-300 file:text-xs file:px-2 file:py-1 cursor-pointer" />
            <p className="text-xs text-slate-400 dark:text-slate-500">รองรับ: PDF, DOCX, XLSX, TXT, MD</p>
            <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400 cursor-pointer select-none">
              <input type="checkbox" checked={deepEnrich} onChange={(e) => setDeepEnrich(e.target.checked)} className="rounded accent-indigo-600" />
              Deep Enrichment (Wiki + QA + Relationships)
            </label>
            <button onClick={uploadFileHandler} disabled={uploading || !uploadFile}
              className="flex items-center justify-center gap-2 rounded-xl bg-slate-800 dark:bg-slate-700 hover:bg-slate-700 dark:hover:bg-slate-600 px-4 py-2 text-sm text-white disabled:opacity-50 transition-colors">
              <Upload size={14} />
              {uploading ? "กำลังอัพโหลด…" : "Upload & Ingest"}
            </button>
          </div>
        </div>
      </div>

      {/* Job result */}
      {jobResult && (
        <div className="rounded-2xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-900 p-4">
          <p className="text-sm font-semibold text-emerald-700 dark:text-emerald-400">✅ Job สร้างแล้ว</p>
          <pre className="text-xs text-emerald-600 dark:text-emerald-500 mt-1">{JSON.stringify(jobResult, null, 2)}</pre>
        </div>
      )}

      {/* Sources list */}
      <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
          แหล่งข้อมูลทั้งหมด ({sources.length})
        </div>
        {loading ? (
          <div className="p-10 text-center text-slate-400 dark:text-slate-600">กำลังโหลด…</div>
        ) : (
          <div>
            {sources.map((src) => (
              <div key={src.id}
                className={`flex items-center gap-3 px-4 py-3 border-b border-slate-100 dark:border-slate-800/80
                            hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors ${!src.is_active ? "opacity-40" : ""}`}>
                <span className="text-xl shrink-0">{typeIcon[src.source_type] || <FileText size={16} className="text-slate-400" />}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-800 dark:text-slate-200 truncate">
                    {src.source_name || src.source_url}
                  </p>
                  {src.source_url && src.source_name && (
                    <a href={src.source_url} target="_blank" rel="noopener noreferrer"
                       className="text-xs text-indigo-500 dark:text-indigo-400 hover:underline truncate block">
                      {src.source_url}
                    </a>
                  )}
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  src.is_active
                    ? "bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-400"
                    : "bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-500"
                }`}>
                  {src.is_active ? "active" : "inactive"}
                </span>
                <button onClick={() => deactivate(src.id)} disabled={!src.is_active}
                  className="flex items-center gap-1 text-xs px-2 py-1 rounded-lg border border-red-200 dark:border-red-900 text-red-500 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/30 disabled:opacity-30 transition-colors">
                  <PowerOff size={11} /> ปิด
                </button>
              </div>
            ))}
            {sources.length === 0 && (
              <div className="p-10 text-center text-slate-400 dark:text-slate-600 text-sm">ยังไม่มีแหล่งข้อมูล</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
