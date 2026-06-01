"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import { ClipboardCheck, Check, X, RefreshCw, FileText, HelpCircle, ChevronDown } from "lucide-react";

interface WikiItem { id: string; title: string; summary: string | null; content_markdown: string; created_at: string }
interface QaItem { id: string; question: string; answer: string; priority: number; created_at: string }
interface Pending { wiki: WikiItem[]; qa: QaItem[]; counts: { wiki: number; qa: number } }

export default function ReviewPage() {
  const [data, setData] = useState<Pending | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<Record<string, boolean>>({});
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const load = useCallback(async () => {
    setLoading(true);
    try { setData(await apiFetch("/api/review/pending").then(r => r.json())); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const act = async (kind: "wiki" | "qa", id: string, action: "approve" | "reject") => {
    setBusy(b => ({ ...b, [id]: true }));
    try {
      await apiFetch(`/api/review/${kind}/${id}/${action}`, { method: "POST" });
      setData(d => d ? {
        ...d,
        [kind]: (d[kind] as (WikiItem | QaItem)[]).filter(x => x.id !== id),
        counts: { ...d.counts, [kind]: d.counts[kind] - 1 },
      } as Pending : d);
    } finally { setBusy(b => ({ ...b, [id]: false })); }
  };

  const total = data ? data.counts.wiki + data.counts.qa : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center shadow-sm shadow-indigo-600/40">
            <ClipboardCheck size={18} className="text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-900 dark:text-white leading-none">Review Queue</h1>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">อนุมัติเนื้อหาที่ AI สร้างก่อนเผยแพร่ {total > 0 ? `· รอ ${total} รายการ` : ""}</p>
          </div>
        </div>
        <button onClick={load} className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800">
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} /> รีเฟรช
        </button>
      </div>

      {!data ? (
        <p className="text-sm text-slate-400 text-center py-10">{loading ? "กำลังโหลด…" : "ไม่มีข้อมูล"}</p>
      ) : total === 0 ? (
        <div className="text-center py-16 text-slate-400">
          <Check size={40} className="mx-auto mb-2 text-emerald-500" />
          <p className="text-sm">ไม่มีเนื้อหารออนุมัติ — ทุกอย่างเผยแพร่แล้ว ✨</p>
        </div>
      ) : (
        <>
          {/* Wiki pending */}
          {data.wiki.length > 0 && (
            <div>
              <h2 className="text-sm font-bold text-slate-700 dark:text-slate-300 mb-2 flex items-center gap-1.5"><FileText size={14} /> Wiki Pages ({data.wiki.length})</h2>
              <div className="space-y-2">
                {data.wiki.map(w => (
                  <div key={w.id} className="rounded-2xl border border-amber-200 dark:border-amber-900/50 bg-amber-50/40 dark:bg-amber-950/10 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="font-semibold text-slate-800 dark:text-white">{w.title}</div>
                        {w.summary && <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-2">{w.summary}</p>}
                      </div>
                      <div className="flex gap-1.5 shrink-0">
                        <button onClick={() => act("wiki", w.id, "approve")} disabled={busy[w.id]} className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-emerald-600 text-white text-xs hover:bg-emerald-700 disabled:opacity-40"><Check size={13} /> อนุมัติ</button>
                        <button onClick={() => act("wiki", w.id, "reject")} disabled={busy[w.id]} className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-600 text-slate-500 text-xs hover:bg-rose-50 dark:hover:bg-rose-950/30 hover:text-rose-600 disabled:opacity-40"><X size={13} /> ปฏิเสธ</button>
                      </div>
                    </div>
                    <button onClick={() => setExpanded(e => ({ ...e, [w.id]: !e[w.id] }))} className="mt-2 flex items-center gap-1 text-xs text-indigo-600 hover:underline">
                      <ChevronDown size={12} className={expanded[w.id] ? "rotate-180" : ""} /> {expanded[w.id] ? "ซ่อน" : "ดู"}เนื้อหา
                    </button>
                    {expanded[w.id] && (
                      <pre className="mt-2 text-xs text-slate-600 dark:text-slate-300 whitespace-pre-wrap bg-white dark:bg-slate-900 rounded-lg p-3 max-h-72 overflow-auto border border-slate-200 dark:border-slate-700">{w.content_markdown}</pre>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* QA pending */}
          {data.qa.length > 0 && (
            <div>
              <h2 className="text-sm font-bold text-slate-700 dark:text-slate-300 mb-2 flex items-center gap-1.5"><HelpCircle size={14} /> Canonical QA ({data.qa.length})</h2>
              <div className="space-y-2">
                {data.qa.map(q => (
                  <div key={q.id} className="rounded-2xl border border-amber-200 dark:border-amber-900/50 bg-amber-50/40 dark:bg-amber-950/10 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="font-medium text-slate-800 dark:text-white text-sm">Q: {q.question}</div>
                        <p className="text-xs text-slate-600 dark:text-slate-300 mt-1">A: {q.answer}</p>
                      </div>
                      <div className="flex gap-1.5 shrink-0">
                        <button onClick={() => act("qa", q.id, "approve")} disabled={busy[q.id]} className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-emerald-600 text-white text-xs hover:bg-emerald-700 disabled:opacity-40"><Check size={13} /> อนุมัติ</button>
                        <button onClick={() => act("qa", q.id, "reject")} disabled={busy[q.id]} className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-600 text-slate-500 text-xs hover:bg-rose-50 dark:hover:bg-rose-950/30 hover:text-rose-600 disabled:opacity-40"><X size={13} /> ปฏิเสธ</button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
