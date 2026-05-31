"use client";

import "./globals.css";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import { getToken, clearToken } from "@/lib/api";
import { ThemeProvider } from "next-themes";
import { useTheme } from "next-themes";
import { Brain, Moon, Sun, LogOut, Menu, X, ChevronDown } from "lucide-react";
import FloatingChat from "@/components/FloatingChat";

// ── Navigation (grouped into dropdown categories) ───────────────────────────────
type NavLink = { href: string; label: string; exact?: boolean };
type NavNode = NavLink | { label: string; children: NavLink[] };

const NAV: NavNode[] = [
  { href: "/chat", label: "💬 Chat", exact: true },
  {
    label: "📚 ความรู้",
    children: [
      { href: "/wiki",    label: "📖 Wiki" },
      { href: "/qa",      label: "❓ QA Editor" },
      { href: "/sources", label: "🔗 Sources" },
      { href: "/graph",   label: "🕸️ Knowledge Graph" },
    ],
  },
  {
    label: "🔧 ระบบงาน",
    children: [
      { href: "/jobs",       label: "⚙️ Jobs" },
      { href: "/unanswered", label: "📭 Missed Questions" },
      { href: "/audit",      label: "📋 Audit Log" },
    ],
  },
  {
    label: "🤖 AI",
    children: [
      { href: "/providers", label: "🤖 Providers" },
      { href: "/eval",      label: "🧪 Evaluation" },
    ],
  },
  { href: "/settings", label: "🛠️ Settings" },
];

const isNavLink = (n: NavNode): n is NavLink => "href" in n;

function isLinkActive(pathname: string, href: string, exact?: boolean): boolean {
  return exact ? pathname === href : pathname.startsWith(href) && href !== "/";
}

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
  const [open, setOpen] = useState(false);            // mobile menu
  const [openMenu, setOpenMenu] = useState<string | null>(null);  // desktop dropdown

  // Close menus whenever the route changes.
  useEffect(() => { setOpen(false); setOpenMenu(null); }, [pathname]);

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
            {NAV.map((node) => {
              // ── Standalone link ──
              if (isNavLink(node)) {
                const active = isLinkActive(pathname, node.href, node.exact);
                return (
                  <Link
                    key={node.href}
                    href={node.href}
                    className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                      active ? "bg-indigo-600 text-white" : "text-slate-400 hover:bg-slate-800 hover:text-white"
                    }`}
                  >
                    {node.label}
                  </Link>
                );
              }
              // ── Dropdown group ──
              const groupActive = node.children.some((c) => isLinkActive(pathname, c.href));
              const isOpen = openMenu === node.label;
              return (
                <div
                  key={node.label}
                  className="relative"
                  onMouseEnter={() => setOpenMenu(node.label)}
                  onMouseLeave={() => setOpenMenu(null)}
                >
                  <button
                    onClick={() => setOpenMenu(isOpen ? null : node.label)}
                    className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                      groupActive || isOpen
                        ? "bg-indigo-600 text-white"
                        : "text-slate-400 hover:bg-slate-800 hover:text-white"
                    }`}
                  >
                    {node.label}
                    <ChevronDown size={13} className={`transition-transform ${isOpen ? "rotate-180" : ""}`} />
                  </button>
                  {isOpen && (
                    <div className="absolute left-0 top-full pt-1.5 z-50 min-w-[210px]">
                      <div className="rounded-xl border border-slate-700/70 bg-slate-900 shadow-xl shadow-black/40 p-1">
                        {node.children.map((c) => {
                          const active = isLinkActive(pathname, c.href);
                          return (
                            <Link
                              key={c.href}
                              href={c.href}
                              className={`block px-3 py-2 rounded-lg text-sm transition-colors ${
                                active ? "bg-indigo-600 text-white" : "text-slate-300 hover:bg-slate-800 hover:text-white"
                              }`}
                            >
                              {c.label}
                            </Link>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
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
            {NAV.map((node) => {
              if (isNavLink(node)) {
                const active = isLinkActive(pathname, node.href, node.exact);
                return (
                  <Link
                    key={node.href}
                    href={node.href}
                    onClick={() => setOpen(false)}
                    className={`px-3 py-2.5 rounded-lg text-sm transition-colors ${
                      active ? "bg-indigo-600 text-white" : "text-slate-300 hover:bg-slate-800 hover:text-white"
                    }`}
                  >
                    {node.label}
                  </Link>
                );
              }
              return (
                <div key={node.label} className="mt-1.5">
                  <div className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                    {node.label}
                  </div>
                  {node.children.map((c) => {
                    const active = isLinkActive(pathname, c.href);
                    return (
                      <Link
                        key={c.href}
                        href={c.href}
                        onClick={() => setOpen(false)}
                        className={`block pl-6 pr-3 py-2.5 rounded-lg text-sm transition-colors ${
                          active ? "bg-indigo-600 text-white" : "text-slate-300 hover:bg-slate-800 hover:text-white"
                        }`}
                      >
                        {c.label}
                      </Link>
                    );
                  })}
                </div>
              );
            })}
            <button
              onClick={() => { setOpen(false); logout(); }}
              className="text-left px-3 py-2.5 mt-1.5 rounded-lg text-sm text-slate-400 hover:bg-slate-800 hover:text-white transition-colors flex items-center gap-1.5 border-t border-slate-800/80 pt-3"
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
    if (pathname === "/login" || pathname === "/" || pathname === "/landing") {
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
    setIsPublicPage(pathname === "/login" || pathname === "/" || pathname === "/landing");
  }, [pathname]);

  return (
    <html lang="th" suppressHydrationWarning>
      <head>
        <title>Enterprise LLM Wiki</title>
        <meta name="description" content="Enterprise LLM Wiki Platform" />
        <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
        <link rel="icon" href="/favicon.ico" type="image/x-icon" />
      </head>
      <body className="min-h-screen bg-slate-100 dark:bg-slate-950 transition-colors duration-200">
        <ThemeProvider attribute="class" defaultTheme="dark" disableTransitionOnChange>
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
            {/* Floating Chat — landing page (customer demo) */}
            {(pathname === "/" || pathname === "/landing") && <FloatingChat />}
          </AuthGuard>
        </ThemeProvider>
      </body>
    </html>
  );
}
