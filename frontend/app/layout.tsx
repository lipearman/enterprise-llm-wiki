"use client";

import "./globals.css";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import { getToken, clearToken } from "@/lib/api";
import { ThemeProvider } from "next-themes";
import { useTheme } from "next-themes";
import { Brain, Moon, Sun, LogOut, Menu, X } from "lucide-react";
import FloatingChat from "@/components/FloatingChat";

const NAV_ITEMS = [
  { href: "/",            label: "💬 Chat",        exact: true  },
  { href: "/wiki",        label: "📖 Wiki",         exact: false },
  { href: "/qa",          label: "❓ QA Editor",    exact: false },
  { href: "/sources",     label: "🔗 Sources",      exact: false },
  { href: "/jobs",        label: "⚙️ Jobs",         exact: false },
  { href: "/graph",       label: "🕸️ Graph",        exact: false },
  { href: "/unanswered",  label: "📭 Missed Q",     exact: false },
];

// ── Theme toggle (used inside NavBar — must render inside ThemeProvider) ──────
function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!mounted) return <div className="w-8 h-8 rounded-lg" />;
  return (
    <button
      onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
      aria-label="สลับธีม"
      className="p-2 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
    >
      {resolvedTheme === "dark"
        ? <Sun size={16} className="text-amber-400" />
        : <Moon size={16} />}
    </button>
  );
}

// ── NavBar ────────────────────────────────────────────────────────────────────
function NavBar() {
  const pathname = usePathname();
  const router   = useRouter();
  const [open, setOpen] = useState(false);

  function logout() {
    clearToken();
    router.replace("/login");
  }

  return (
    <nav className="bg-slate-950 border-b border-slate-800/80 text-white">
      <div className="mx-auto max-w-7xl px-4">
        <div className="flex h-14 items-center justify-between">

          {/* Logo */}
          <Link href="/" className="flex items-center gap-2.5 font-bold text-base tracking-tight shrink-0">
            <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center shadow-sm shadow-indigo-600/40">
              <Brain size={15} className="text-white" />
            </div>
            <span className="hidden sm:block">Enterprise LLM Wiki</span>
          </Link>

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-0.5">
            {NAV_ITEMS.map((item) => {
              const active = item.exact
                ? pathname === item.href
                : pathname.startsWith(item.href) && item.href !== "/";
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    active
                      ? "bg-indigo-600 text-white"
                      : "text-slate-400 hover:bg-slate-800 hover:text-white"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </div>

          {/* Right: theme toggle + logout */}
          <div className="hidden md:flex items-center gap-1">
            <ThemeToggle />
            <div className="w-px h-4 bg-slate-700 mx-1" />
            <button
              onClick={logout}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium
                         text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
              title="ออกจากระบบ"
            >
              <LogOut size={14} />
              ออกจากระบบ
            </button>
          </div>

          {/* Mobile: theme toggle + hamburger */}
          <div className="md:hidden flex items-center gap-1">
            <ThemeToggle />
            <button
              className="p-2 rounded-lg text-slate-400 hover:bg-slate-800 transition-colors"
              onClick={() => setOpen(!open)}
            >
              {open ? <X size={18} /> : <Menu size={18} />}
            </button>
          </div>
        </div>

        {/* Mobile dropdown */}
        {open && (
          <div className="md:hidden pb-3 flex flex-col gap-0.5 border-t border-slate-800/80 mt-1 pt-2">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setOpen(false)}
                className="px-3 py-2.5 rounded-lg text-sm text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
              >
                {item.label}
              </Link>
            ))}
            <button
              onClick={() => { setOpen(false); logout(); }}
              className="text-left px-3 py-2.5 rounded-lg text-sm text-slate-400 hover:bg-slate-800 hover:text-white transition-colors flex items-center gap-1.5"
            >
              <LogOut size={14} />
              ออกจากระบบ
            </button>
          </div>
        )}
      </div>
    </nav>
  );
}

// ── Auth Guard ────────────────────────────────────────────────────────────────
function AuthGuard({ children }: { children: React.ReactNode }) {
  const router   = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (pathname === "/login" || pathname === "/landing") {
      setReady(true);
      return;
    }
    const token = getToken();
    if (!token) {
      router.replace("/login");
    } else {
      setReady(true);
    }
  }, [pathname, router]);

  if (!ready) {
    return (
      <div className="flex h-screen items-center justify-center text-slate-400 dark:text-slate-600 text-sm">
        กำลังตรวจสอบสิทธิ์…
      </div>
    );
  }
  return <>{children}</>;
}

// ── Root Layout ───────────────────────────────────────────────────────────────
export default function RootLayout({ children }: { children: React.ReactNode }) {
  const [isPublicPage, setIsPublicPage] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    setIsPublicPage(pathname === "/login" || pathname === "/landing");
  }, [pathname]);

  return (
    <html lang="th" suppressHydrationWarning>
      <head>
        <title>Enterprise LLM Wiki</title>
        <meta name="description" content="Enterprise LLM Wiki Platform" />
      </head>
      <body className="min-h-screen bg-slate-100 dark:bg-slate-950 transition-colors duration-200">
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
          <AuthGuard>
            {!isPublicPage && <NavBar />}
            <main className={isPublicPage ? "" : "mx-auto max-w-7xl px-4 py-6"}>
              {children}
            </main>
            {!isPublicPage && (
              <footer className="text-center text-xs text-slate-400 dark:text-slate-600 py-4">
                Enterprise LLM Wiki v0.2.0 · Powered by Ollama + Supabase
              </footer>
            )}
            {/* Floating Chat — landing page only (customer demo) */}
            {pathname === "/landing" && <FloatingChat />}
          </AuthGuard>
        </ThemeProvider>
      </body>
    </html>
  );
}
