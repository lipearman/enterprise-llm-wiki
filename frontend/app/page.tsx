"use client";

import { useState, useRef, useEffect } from "react";
import { apiFetch, API_BASE } from "@/lib/api";
import { Bot, Send, BookOpen } from "lucide-react";

const DEFAULT_COMPANY = process.env.NEXT_PUBLIC_COMPANY_CODE || "DEVES";

type SourceRef = { label: string; url?: string | null };
type Message   = { role: "user" | "assistant"; text: string; mode?: string; sources?: any[]; source_refs?: SourceRef[] };

const MODE_BADGE: Record<string, string> = {
  answer_cache: "bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-400",
  canonical_qa: "bg-blue-100  dark:bg-blue-900/40  text-blue-700  dark:text-blue-400",
  rag:          "bg-violet-100 dark:bg-violet-900/40 text-violet-700 dark:text-violet-400",
  error:        "bg-red-100   dark:bg-red-900/40   text-red-700   dark:text-red-400",
};

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput]       = useState("");
  const [company, setCompany]   = useState(DEFAULT_COMPANY);
  const [loading, setLoading]   = useState(false);
  const [forceRag, setForceRag] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const sessionId = useRef<string>(
    typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID()
      : Math.random().toString(36).slice(2)
  );

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send() {
    const q = input.trim();
    if (!q || loading) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: q }]);
    setLoading(true);
    try {
      const res = await apiFetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q, company_code: company, force_rag: forceRag, session_id: sessionId.current }),
      });
      let data: any = null;
      try { data = await res.json(); } catch { data = null; }
      if (!res.ok || !data) {
        const detail = data?.detail ?? `HTTP ${res.status}`;
        setMessages((m) => [...m, { role: "assistant", text: `❌ ระบบขัดข้อง: ${detail} — กรุณาลองใหม่อีกครั้ง` }]);
        return;
      }
      setMessages((m) => [...m, {
        role: "assistant",
        text: data.answer || JSON.stringify(data),
        mode: data.mode,
        sources: data.sources,
        source_refs: data.source_refs,
      }]);
    } catch (e: any) {
      setMessages((m) => [...m, { role: "assistant", text: `❌ เชื่อมต่อไม่ได้: ${e.message}` }]);
    } finally {
      setLoading(false);
    }
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 p-5 shadow-sm flex flex-wrap items-center gap-4">
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
            <Bot size={22} className="text-indigo-500" /> Chat Assistant
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            4-layer retrieval: Cache → Canonical QA → Wiki → Chunks
          </p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <label className="text-sm font-medium text-slate-600 dark:text-slate-400">Company:</label>
          <select
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800
                       text-slate-800 dark:text-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="DEVES">DEVES</option>
            <option value="LOCKTON">LOCKTON</option>
          </select>
          <label className="flex items-center gap-1.5 text-sm text-slate-600 dark:text-slate-400 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={forceRag}
              onChange={(e) => setForceRag(e.target.checked)}
              className="rounded accent-indigo-600"
            />
            Force RAG
          </label>
        </div>
      </div>

      {/* Chat area */}
      <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm flex flex-col"
           style={{ minHeight: "65vh" }}>
        <div className="flex-1 overflow-y-auto p-5 space-y-4" style={{ maxHeight: "65vh" }}>
          {messages.length === 0 && (
            <div className="text-center text-slate-400 dark:text-slate-600 mt-20">
              <div className="w-16 h-16 rounded-2xl bg-indigo-100 dark:bg-indigo-950 flex items-center justify-center mx-auto mb-4">
                <Bot size={32} className="text-indigo-500" />
              </div>
              <p className="text-lg font-medium text-slate-600 dark:text-slate-400">เริ่มถามคำถามได้เลย</p>
              <p className="text-sm mt-1 text-slate-400 dark:text-slate-500">
                เช่น "ประกันรถยนต์ชั้น 1 คืออะไร" หรือ "วิธีแจ้งอุบัติเหตุ"
              </p>
            </div>
          )}
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-2xl rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap shadow-sm ${
                msg.role === "user"
                  ? "bg-indigo-600 text-white rounded-br-sm"
                  : "bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 rounded-bl-sm"
              }`}>
                {msg.text}

                {/* Source references */}
                {msg.source_refs && msg.source_refs.length > 0 && (
                  <div className="mt-3 pt-2 border-t border-slate-300 dark:border-slate-600">
                    <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1 flex items-center gap-1">
                      <BookOpen size={11} /> แหล่งอ้างอิง
                    </p>
                    <ul className="space-y-0.5">
                      {msg.source_refs.map((ref, j) => (
                        <li key={j} className="text-xs text-slate-600 dark:text-slate-400 flex items-center gap-1.5">
                          <span className="text-slate-400 dark:text-slate-500">•</span>
                          <span>{ref.label}</span>
                          {ref.url && (
                            <a href={ref.url} target="_blank" rel="noopener noreferrer"
                               className="text-indigo-500 dark:text-indigo-400 hover:underline whitespace-nowrap">
                              [คลิก link]
                            </a>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Mode badge */}
                {msg.mode && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${MODE_BADGE[msg.mode] || "bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300"}`}>
                      {msg.mode}
                    </span>
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-slate-100 dark:bg-slate-800 rounded-2xl rounded-bl-sm px-4 py-3">
                <span className="inline-flex gap-1">
                  {[0, 150, 300].map((d) => (
                    <span key={d} className="w-2 h-2 bg-indigo-400 dark:bg-indigo-500 rounded-full animate-bounce"
                          style={{ animationDelay: `${d}ms` }} />
                  ))}
                </span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input area */}
        <div className="border-t border-slate-200 dark:border-slate-800 p-4 flex gap-3">
          <textarea
            rows={2}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="พิมพ์คำถาม… (Enter ส่ง, Shift+Enter ขึ้นบรรทัด)"
            className="flex-1 resize-none rounded-xl border border-slate-200 dark:border-slate-700
                       bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200
                       placeholder-slate-400 dark:placeholder-slate-500
                       px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-shadow"
          />
          <button
            onClick={send}
            disabled={loading || !input.trim()}
            className="self-end rounded-xl bg-indigo-600 hover:bg-indigo-700 px-5 py-2.5
                       text-sm font-semibold text-white disabled:opacity-40 transition-colors
                       shadow-md shadow-indigo-600/20 flex items-center gap-1.5"
          >
            <Send size={15} />
            ส่ง
          </button>
        </div>
      </div>
    </div>
  );
}
