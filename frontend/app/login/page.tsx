"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { setToken, TOKEN_KEY, API_BASE } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [apiKey, setApiKey] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!apiKey.trim()) return;
    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${API_BASE}/api/auth/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: apiKey.trim() }),
      });

      if (res.ok) {
        setToken(apiKey.trim());
        router.replace("/");
      } else {
        const data = await res.json().catch(() => ({}));
        setError(data.detail || "API key ไม่ถูกต้อง");
      }
    } catch {
      setError("ไม่สามารถเชื่อมต่อกับ server ได้");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50
                    dark:from-slate-950 dark:via-slate-950 dark:to-indigo-950/50
                    flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Back link */}
        <div className="mb-6 text-center">
          <Link href="/landing"
            className="inline-flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400
                       hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">
            ← กลับหน้าหลัก
          </Link>
        </div>

        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-indigo-600 flex items-center justify-center mx-auto mb-4 shadow-lg shadow-indigo-600/30">
            <span className="text-3xl">🧠</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-800 dark:text-white">Enterprise LLM Wiki</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">กรุณาใส่ API Key เพื่อเข้าใช้งาน</p>
        </div>

        {/* Card */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-xl shadow-slate-200/80 dark:shadow-slate-950/80 border border-slate-200/80 dark:border-slate-800 p-6">
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                API Key
              </label>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="••••••••••••••••••••••"
                autoFocus
                autoComplete="current-password"
                className="w-full rounded-xl border border-slate-200 dark:border-slate-700
                           bg-white dark:bg-slate-800 px-3 py-2.5 text-sm
                           text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500
                           focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-shadow"
              />
            </div>

            {/* Demo key hint */}
            <div className="rounded-xl bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800 px-3.5 py-3">
              <p className="text-xs font-semibold text-indigo-700 dark:text-indigo-300 mb-1.5">
                🔑 Demo Key สำหรับทดสอบระบบ
              </p>
              <div className="flex items-center gap-2">
                <code className="flex-1 text-xs font-mono text-indigo-800 dark:text-indigo-200 bg-white dark:bg-slate-900 px-2 py-1.5 rounded-lg border border-indigo-200 dark:border-indigo-700 select-all truncate">
                  changeme-enterprise-wiki-2025
                </code>
                <button
                  type="button"
                  onClick={() => setApiKey("changeme-enterprise-wiki-2025")}
                  className="shrink-0 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 text-white hover:bg-indigo-700 transition-colors"
                >
                  ใช้งาน
                </button>
              </div>
            </div>

            {error && (
              <div className="rounded-lg bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-900 px-3 py-2 text-sm text-red-600 dark:text-red-400">
                ❌ {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !apiKey.trim()}
              className="rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white
                         hover:bg-indigo-700 disabled:opacity-50 transition-colors
                         shadow-md shadow-indigo-600/30"
            >
              {loading ? "กำลังตรวจสอบ…" : "🔐 เข้าสู่ระบบ"}
            </button>
          </form>
        </div>

        <p className="text-center text-xs text-slate-400 dark:text-slate-600 mt-6">
          Enterprise LLM Wiki v0.2.0
        </p>
      </div>
    </div>
  );
}
