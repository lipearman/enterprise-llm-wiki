"use client";

import "./globals.css";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const NAV_ITEMS = [
  { href: "/",          label: "💬 Chat",        exact: true },
  { href: "/wiki",      label: "📖 Wiki Pages",   exact: false },
  { href: "/qa",        label: "❓ QA Editor",    exact: false },
  { href: "/sources",   label: "🔗 Sources",      exact: false },
  { href: "/jobs",      label: "⚙️ Jobs",         exact: false },
];

function NavBar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  return (
    <nav className="bg-slate-900 text-white shadow-lg">
      <div className="mx-auto max-w-7xl px-4">
        <div className="flex h-14 items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-lg tracking-tight">
            <span className="text-blue-400">🧠</span>
            <span>Enterprise LLM Wiki</span>
          </Link>

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-1">
            {NAV_ITEMS.map((item) => {
              const active = item.exact ? pathname === item.href : pathname.startsWith(item.href) && item.href !== "/";
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    active ? "bg-blue-600 text-white" : "text-slate-300 hover:bg-slate-700 hover:text-white"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </div>

          {/* Mobile hamburger */}
          <button className="md:hidden p-2 rounded-lg hover:bg-slate-700" onClick={() => setOpen(!open)}>
            <span className="text-xl">{open ? "✕" : "☰"}</span>
          </button>
        </div>

        {/* Mobile dropdown */}
        {open && (
          <div className="md:hidden pb-3 flex flex-col gap-1">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setOpen(false)}
                className="px-3 py-2 rounded-lg text-sm hover:bg-slate-700"
              >
                {item.label}
              </Link>
            ))}
          </div>
        )}
      </div>
    </nav>
  );
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="th">
      <head>
        <title>Enterprise LLM Wiki</title>
        <meta name="description" content="Enterprise LLM Wiki Platform" />
      </head>
      <body className="min-h-screen bg-slate-100">
        <NavBar />
        <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
        <footer className="text-center text-xs text-slate-400 py-4">
          Enterprise LLM Wiki v0.2.0 · Powered by Ollama + Supabase
        </footer>
      </body>
    </html>
  );
}
