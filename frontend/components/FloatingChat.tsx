"use client";

import { useEffect, useRef, useState } from "react";
import { useTheme } from "next-themes";
import { API_BASE } from "@/lib/api";
import { Bot, X, Send, MessageCircle, BookOpen, Sun, Moon, RotateCcw } from "lucide-react";

const DEFAULT_COMPANY: Company = {
  code: process.env.NEXT_PUBLIC_COMPANY_CODE || "DEVES",
  name: process.env.NEXT_PUBLIC_COMPANY_CODE || "DEVES",
};

interface Company { code: string; name: string; }
interface SourceRef { title: string; url?: string | null; }
interface Message {
  id: string;
  role: "user" | "bot";
  text: string;
  sources?: SourceRef[];
}

// ── Inline markdown renderer (bold + links) ───────────────────────────────────
function RenderText({ text }: { text: string }) {
  const parts = text.split(
    /(\*\*[^*]+\*\*|\[[^\]]+\]\(https?:\/\/[^)]+\)|https?:\/\/[^\s)>,"]+)/g
  );
  return (
    <>
      {parts.map((p, i) => {
        if (p.startsWith("**") && p.endsWith("**"))
          return <strong key={i}>{p.slice(2, -2)}</strong>;
        const mdLink = p.match(/^\[([^\]]+)\]\((https?:\/\/[^)]+)\)$/);
        if (mdLink)
          return (
            <a key={i} href={mdLink[2]} target="_blank" rel="noopener noreferrer"
               className="text-indigo-500 dark:text-indigo-400 underline break-all">
              {mdLink[1]}
            </a>
          );
        if (p.match(/^https?:\/\//))
          return (
            <a key={i} href={p} target="_blank" rel="noopener noreferrer"
               className="text-indigo-500 dark:text-indigo-400 underline break-all">
              {p}
            </a>
          );
        return <span key={i}>{p}</span>;
      })}
    </>
  );
}

// ── Typing dots ───────────────────────────────────────────────────────────────
function TypingDots() {
  return (
    <span className="inline-flex gap-1 items-center h-4">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-1.5 w-1.5 rounded-full bg-slate-400 dark:bg-slate-500 animate-bounce"
          style={{ animationDelay: `${i * 150}ms` }}
        />
      ))}
    </span>
  );
}

// ── Session ID helper ─────────────────────────────────────────────────────────
function newSessionId(): string {
  return typeof crypto !== "undefined" && crypto.randomUUID
    ? `pub_${crypto.randomUUID()}`
    : `pub_${Math.random().toString(36).slice(2)}`;
}

// ── Main component ────────────────────────────────────────────────────────────
export default function FloatingChat() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted,   setMounted]   = useState(false);
  const [open,      setOpen]      = useState(false);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [company,   setCompany]   = useState<Company>(DEFAULT_COMPANY);
  const [messages,  setMessages]  = useState<Message[]>([]);
  const [input,     setInput]     = useState("");
  const [loading,     setLoading]     = useState(false);
  const [streamingId, setStreamingId] = useState<string | null>(null);
  const bottomRef  = useRef<HTMLDivElement>(null);
  const inputRef   = useRef<HTMLTextAreaElement>(null);
  // Stable session ID — persists across turns, reset on new session
  const sessionId  = useRef<string>(newSessionId());

  // Mounted guard (next-themes hydration)
  useEffect(() => setMounted(true), []);

  // Load companies once — sessionStorage cache (5 min) to avoid re-fetching
  useEffect(() => {
    const CACHE_KEY = "pub_companies_v1";
    const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

    // Try cache first
    try {
      const raw = sessionStorage.getItem(CACHE_KEY);
      if (raw) {
        const { data, ts } = JSON.parse(raw) as { data: Company[]; ts: number };
        if (Date.now() - ts < CACHE_TTL && Array.isArray(data) && data.length > 0) {
          setCompanies(data);
          setCompany(data[0]);
          return;
        }
      }
    } catch { /* ignore parse errors */ }

    // Fetch from backend
    fetch(`${API_BASE}/api/public/companies`)
      .then((r) => r.json())
      .then((data: Company[]) => {
        if (Array.isArray(data) && data.length > 0) {
          setCompanies(data);
          setCompany(data[0]);
          try {
            sessionStorage.setItem(CACHE_KEY, JSON.stringify({ data, ts: Date.now() }));
          } catch { /* storage full — ignore */ }
        }
      })
      .catch(() => {
        // backend not yet available — default company still set, chat still works
      });
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Focus input on open
  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 150);
  }, [open]);

  // Close on Escape
  useEffect(() => {
    const fn = (e: KeyboardEvent) => { if (e.key === "Escape" && open) setOpen(false); };
    window.addEventListener("keydown", fn);
    return () => window.removeEventListener("keydown", fn);
  }, [open]);

  const send = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const uid = Date.now().toString();
    const bid = uid + "b";

    setMessages((m) => [
      ...m,
      { id: uid, role: "user", text },
      { id: bid, role: "bot",  text: "…" },
    ]);
    setInput("");
    setLoading(true);
    setStreamingId(bid);

    try {
      const res = await fetch(`${API_BASE}/api/public/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message:      text,
          company_code: company.code,
          session_id:   sessionId.current,
        }),
      });

      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

      const reader  = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer      = "";
      let accumulated = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";

        for (const part of parts) {
          if (!part.startsWith("data: ")) continue;
          let payload: {
            token?: string;
            done?: boolean;
            sources?: SourceRef[];
            error?: string;
            status?: string;   // "thinking" heartbeat — keep-alive, no UI change
          };
          try { payload = JSON.parse(part.slice(6)); }
          catch { continue; }

          // Heartbeat — just keep the connection alive, typing dots already showing
          if (payload.status === "thinking") continue;

          if (payload.token !== undefined) {
            accumulated += payload.token;
            setMessages((m) =>
              m.map((msg) =>
                msg.id === bid ? { ...msg, text: accumulated || "…" } : msg
              )
            );
          }
          if (payload.done) {
            const sources: SourceRef[] = payload.sources ?? [];
            setMessages((m) =>
              m.map((msg) =>
                msg.id === bid
                  ? { ...msg, text: accumulated || "ขออภัย ไม่ได้รับคำตอบ", sources }
                  : msg
              )
            );
          }
        }
      }
    } catch {
      setMessages((m) =>
        m.map((msg) =>
          msg.id === bid
            ? { ...msg, text: "ขออภัย เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง" }
            : msg
        )
      );
    } finally {
      setLoading(false);
      setStreamingId(null);
    }
  };

  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  };

  // Don't render theme-dependent UI until mounted
  if (!mounted) return null;

  const isDark = resolvedTheme === "dark";

  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col items-end gap-3">

      {/* ── Chat window ───────────────────────────────────────────────────── */}
      {open && (
        <div className="flex h-[540px] w-[360px] max-w-[calc(100vw-2.5rem)] flex-col
                        rounded-2xl border border-slate-200 dark:border-slate-700
                        bg-white dark:bg-slate-900 shadow-2xl overflow-hidden
                        animate-fade-up">

          {/* Header */}
          <div className="flex items-center gap-2.5 border-b border-slate-200 dark:border-slate-700
                          bg-gradient-to-r from-indigo-600 to-violet-600 px-4 py-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-full
                            bg-white/20 backdrop-blur-sm shrink-0">
              <Bot size={16} className="text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-white leading-none tracking-wide">J.A.R.V.I.S.</p>
              <p className="text-[11px] text-indigo-100 mt-0.5">ผู้ช่วยฐานความรู้ AI</p>
            </div>
            <div className="flex items-center gap-1">
              {/* New chat / reset session */}
              {messages.length > 0 && (
                <button
                  onClick={() => {
                    setMessages([]);
                    sessionId.current = newSessionId();
                  }}
                  className="p-1.5 rounded-lg text-white/70 hover:bg-white/20 transition-colors"
                  aria-label="เริ่มการสนทนาใหม่"
                  title="เริ่มการสนทนาใหม่"
                >
                  <RotateCcw size={13} />
                </button>
              )}
              {/* Theme toggle */}
              <button
                onClick={() => setTheme(isDark ? "light" : "dark")}
                className="p-1.5 rounded-lg text-white/70 hover:bg-white/20 transition-colors"
                aria-label="สลับธีม"
              >
                {isDark
                  ? <Sun size={14} className="text-amber-300" />
                  : <Moon size={14} />}
              </button>
              <button
                onClick={() => setOpen(false)}
                className="p-1.5 rounded-lg text-white/70 hover:bg-white/20 transition-colors"
                aria-label="ปิด"
              >
                <X size={15} />
              </button>
            </div>
          </div>

          {/* Company selector */}
          <div className="border-b border-slate-200 dark:border-slate-700/80 px-4 py-2
                          bg-slate-50 dark:bg-slate-800/50">
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-slate-500 dark:text-slate-400 shrink-0">
                ฐานความรู้:
              </span>
              <select
                value={company.code}
                onChange={(e) => {
                  const c = companies.find((x) => x.code === e.target.value);
                  if (c) {
                    setCompany(c);
                    setMessages([]);
                    sessionId.current = newSessionId(); // new session on company switch
                  }
                }}
                className="flex-1 rounded-lg border border-slate-200 dark:border-slate-600
                           bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-200
                           px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                {!Array.isArray(companies) || companies.length === 0
                  ? <option value={company.code}>{company.name}</option>
                  : companies.map((c) => (
                      <option key={c.code} value={c.code}>{c.name}</option>
                    ))
                }
              </select>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 scroll-smooth">
            {messages.length === 0 && (
              <div className="flex h-full flex-col items-center justify-center text-center gap-3 text-slate-400 dark:text-slate-500">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-600 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-600/30">
                  <Bot size={30} className="text-white" />
                </div>
                <div>
                  <p className="text-sm font-bold text-slate-700 dark:text-slate-200 tracking-wide">J.A.R.V.I.S.</p>
                  <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5 leading-relaxed">
                    สวัสดีครับ พร้อมตอบคำถาม<br />
                    เกี่ยวกับ {company.name} ครับ
                  </p>
                </div>
              </div>
            )}

            {messages.map((m) => (
              <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed ${
                  m.role === "user"
                    ? "bg-indigo-600 text-white rounded-br-sm"
                    : "bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 rounded-bl-sm border border-slate-200 dark:border-slate-700"
                }`}>
                  {m.text === "…"
                    ? <TypingDots />
                    : (
                      <>
                        <p className="whitespace-pre-wrap">
                          <RenderText text={m.text} />
                          {m.id === streamingId && (
                            <span className="inline-block w-0.5 h-[1em] bg-current align-middle ml-0.5 animate-pulse" />
                          )}
                        </p>
                        {/* Sources — shown only when backend deems content too rich */}
                        {m.role === "bot" && m.sources && m.sources.length > 0 && (
                          <div className="mt-2.5 pt-2 border-t border-indigo-200 dark:border-slate-600 space-y-1.5">
                            <p className="text-[10px] font-semibold text-indigo-500 dark:text-indigo-400 uppercase tracking-wide flex items-center gap-1">
                              <BookOpen size={9} /> แหล่งข้อมูล
                            </p>
                            {m.sources.map((s, i) => (
                              <div key={i} className="flex items-center gap-1.5 text-xs opacity-80">
                                <span className="w-1 h-1 rounded-full bg-indigo-400 shrink-0" />
                                {s.url
                                  ? <a href={s.url} target="_blank" rel="noopener noreferrer"
                                       className="underline hover:opacity-100 truncate">
                                      {s.title}
                                    </a>
                                  : <span className="truncate">{s.title}</span>
                                }
                              </div>
                            ))}
                          </div>
                        )}
                      </>
                    )
                  }
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>

          {/* Input bar */}
          <div className="border-t border-slate-200 dark:border-slate-700 px-3 py-2.5
                          bg-white dark:bg-slate-900">
            <div className="flex items-end gap-2 rounded-xl border border-slate-200 dark:border-slate-700
                            bg-slate-50 dark:bg-slate-800 px-3 py-2 focus-within:ring-2
                            focus-within:ring-indigo-500 focus-within:border-transparent transition-all">
              <textarea
                ref={inputRef}
                rows={1}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKey}
                disabled={loading}
                placeholder="พิมพ์คำถาม… (Enter ส่ง)"
                className="flex-1 resize-none bg-transparent text-sm text-slate-800 dark:text-slate-200
                           outline-none placeholder:text-slate-400 dark:placeholder:text-slate-500
                           disabled:opacity-50"
                style={{ maxHeight: 80 }}
              />
              <button
                onClick={send}
                disabled={loading || !input.trim()}
                className="mb-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg
                           bg-indigo-600 hover:bg-indigo-700 text-white
                           disabled:opacity-40 transition-colors"
                aria-label="ส่ง"
              >
                {loading
                  ? <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3"/>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                    </svg>
                  : <Send size={14} />
                }
              </button>
            </div>
            <p className="mt-1 text-center text-[10px] text-slate-400 dark:text-slate-600">
              คำตอบจากฐานความรู้จริง — กรุณาตรวจสอบข้อมูลสำคัญ
            </p>
          </div>
        </div>
      )}

      {/* ── Toggle button ──────────────────────────────────────────────────── */}
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? "ปิด chatbot" : "เปิด chatbot"}
        className="relative flex h-14 w-14 items-center justify-center rounded-full
                   bg-gradient-to-br from-indigo-600 to-violet-600 text-white
                   shadow-lg shadow-indigo-600/40 hover:shadow-indigo-600/60
                   hover:scale-105 active:scale-95 transition-all duration-200"
      >
        {/* Ping badge when closed */}
        {!open && (
          <span className="absolute -top-1 -right-1 flex h-3.5 w-3.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-indigo-400 opacity-75" />
            <span className="relative inline-flex h-3.5 w-3.5 rounded-full bg-indigo-500" />
          </span>
        )}
        {open
          ? <X size={22} />
          : <MessageCircle size={22} />
        }
      </button>
    </div>
  );
}
