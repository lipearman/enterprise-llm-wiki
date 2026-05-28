"use client";

import { useState, useRef, useEffect } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8080";
const DEFAULT_COMPANY = process.env.NEXT_PUBLIC_COMPANY_CODE || "DEVES";

type Message = { role: "user" | "assistant"; text: string; mode?: string; sources?: any[] };

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [company, setCompany] = useState(DEFAULT_COMPANY);
  const [loading, setLoading] = useState(false);
  const [forceRag, setForceRag] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

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
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q, company_code: company, force_rag: forceRag }),
      });
      const data = await res.json();
      setMessages((m) => [
        ...m,
        { role: "assistant", text: data.answer || JSON.stringify(data), mode: data.mode, sources: data.sources },
      ]);
    } catch (e: any) {
      setMessages((m) => [...m, { role: "assistant", text: `❌ Error: ${e.message}` }]);
    } finally {
      setLoading(false);
    }
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  }

  const modeColor: Record<string, string> = {
    answer_cache: "bg-green-100 text-green-700",
    canonical_qa: "bg-blue-100 text-blue-700",
    rag: "bg-violet-100 text-violet-700",
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-2xl bg-white p-5 shadow-sm flex flex-wrap items-center gap-4">
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-slate-800">💬 Chat Assistant</h1>
          <p className="text-sm text-slate-500 mt-0.5">4-layer retrieval: Cache → Canonical QA → Wiki → Chunks</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="text-sm font-medium text-slate-600">Company:</label>
          <select value={company} onChange={(e) => setCompany(e.target.value)} className="rounded-lg border px-3 py-1.5 text-sm">
            <option value="DEVES">DEVES</option>
            <option value="LOCKTON">LOCKTON</option>
          </select>
          <label className="flex items-center gap-1.5 text-sm text-slate-600 cursor-pointer">
            <input type="checkbox" checked={forceRag} onChange={(e) => setForceRag(e.target.checked)} className="rounded" />
            Force RAG
          </label>
        </div>
      </div>

      <div className="rounded-2xl bg-white shadow-sm flex flex-col" style={{ minHeight: "65vh" }}>
        <div className="flex-1 overflow-y-auto p-5 space-y-4" style={{ maxHeight: "65vh" }}>
          {messages.length === 0 && (
            <div className="text-center text-slate-400 mt-20">
              <div className="text-5xl mb-3">🤖</div>
              <p className="text-lg font-medium">เริ่มถามคำถามได้เลย</p>
              <p className="text-sm mt-1">เช่น "ประกันรถยนต์ชั้น 1 คืออะไร" หรือ "วิธีแจ้งอุบัติเหตุ"</p>
            </div>
          )}
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-2xl rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap ${
                msg.role === "user" ? "bg-blue-600 text-white rounded-br-sm" : "bg-slate-100 text-slate-800 rounded-bl-sm"
              }`}>
                {msg.text}
                {msg.mode && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${modeColor[msg.mode] || "bg-slate-200"}`}>
                      {msg.mode}
                    </span>
                    {(msg.sources || []).slice(0, 3).map((s: any, j: number) => (
                      <span key={j} title={s.title} className="text-xs px-2 py-0.5 bg-slate-200 text-slate-600 rounded-full truncate max-w-[180px]">
                        {s.title || s.source_type}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-slate-100 rounded-2xl rounded-bl-sm px-4 py-3">
                <span className="inline-flex gap-1">
                  {[0, 150, 300].map((d) => (
                    <span key={d} className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: `${d}ms` }} />
                  ))}
                </span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
        <div className="border-t p-4 flex gap-3">
          <textarea
            rows={2}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="พิมพ์คำถาม… (Enter ส่ง, Shift+Enter ขึ้นบรรทัด)"
            className="flex-1 resize-none rounded-xl border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={send}
            disabled={loading || !input.trim()}
            className="self-end rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-40 transition-colors"
          >
            ส่ง
          </button>
        </div>
      </div>
    </div>
  );
}
