"use client";

import Link from "next/link";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import {
  Brain, Search, MessageSquare, BookOpen, Building2, Shield,
  Zap, Network, Moon, Sun, CheckCircle, ArrowRight, Database,
  Code2, Layers, Users, TrendingUp, Server, FileText, Bot,
  Sparkles, ChevronRight, RefreshCw, Lock, Globe, BarChart3,
  GitBranch, Cpu, HardDrive
} from "lucide-react";

// ── Theme Toggle ─────────────────────────────────────────────────────────────
function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!mounted) return <div className="w-9 h-9 rounded-lg border border-slate-200" />;
  return (
    <button
      onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
      aria-label="สลับธีม"
      className="p-2.5 rounded-lg border border-slate-200 dark:border-slate-700
                 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700
                 transition-all duration-200 shadow-sm"
    >
      {resolvedTheme === "dark"
        ? <Sun size={17} className="text-amber-400" />
        : <Moon size={17} className="text-slate-500" />}
    </button>
  );
}

// ── Navbar ────────────────────────────────────────────────────────────────────
function LandingNav() {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 30);
    window.addEventListener("scroll", fn);
    return () => window.removeEventListener("scroll", fn);
  }, []);

  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
      scrolled
        ? "bg-white/90 dark:bg-slate-950/90 backdrop-blur-xl shadow-sm border-b border-slate-200/80 dark:border-slate-800/80"
        : "bg-transparent"
    }`}>
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-indigo-600 flex items-center justify-center shadow-md shadow-indigo-600/30">
              <Brain size={18} className="text-white" />
            </div>
            <span className="font-bold text-base text-slate-900 dark:text-white tracking-tight">
              Enterprise LLM Wiki
            </span>
          </div>

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-7">
            {[["#features", "ฟีเจอร์"], ["#how-it-works", "ขั้นตอน"], ["#scale", "ขนาดองค์กร"], ["#tech", "เทคโนโลยี"]].map(([href, label]) => (
              <a key={href} href={href}
                className="text-sm text-slate-600 dark:text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors font-medium">
                {label}
              </a>
            ))}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2.5">
            <ThemeToggle />
            <Link href="/login"
              className="hidden sm:inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700
                         text-white text-sm font-semibold transition-colors shadow-md shadow-indigo-600/30">
              เข้าสู่ระบบ <ChevronRight size={14} />
            </Link>
            <button className="md:hidden p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              onClick={() => setMenuOpen(!menuOpen)}>
              <div className="w-5 h-0.5 bg-slate-700 dark:bg-slate-300 mb-1 transition-all" />
              <div className="w-5 h-0.5 bg-slate-700 dark:bg-slate-300 mb-1" />
              <div className="w-5 h-0.5 bg-slate-700 dark:bg-slate-300" />
            </button>
          </div>
        </div>

        {/* Mobile menu */}
        {menuOpen && (
          <div className="md:hidden pb-4 border-t border-slate-200 dark:border-slate-800 mt-1">
            {[["#features", "ฟีเจอร์"], ["#how-it-works", "ขั้นตอน"], ["#scale", "ขนาดองค์กร"], ["#tech", "เทคโนโลยี"]].map(([href, label]) => (
              <a key={href} href={href} onClick={() => setMenuOpen(false)}
                className="block py-2.5 px-1 text-sm text-slate-700 dark:text-slate-300 hover:text-indigo-600 dark:hover:text-indigo-400">
                {label}
              </a>
            ))}
            <Link href="/login" onClick={() => setMenuOpen(false)}
              className="mt-2 block text-center px-4 py-2.5 rounded-xl bg-indigo-600 text-white text-sm font-semibold">
              เข้าสู่ระบบ
            </Link>
          </div>
        )}
      </div>
    </nav>
  );
}

// ── Mock Chat Card (hero visual) ──────────────────────────────────────────────
function MockChat() {
  return (
    <div className="relative w-full max-w-sm mx-auto animate-float">
      {/* Glow behind card */}
      <div className="absolute -inset-4 bg-indigo-500/20 dark:bg-indigo-600/30 rounded-3xl blur-2xl" />
      <div className="relative rounded-2xl border border-slate-200 dark:border-slate-700
                      bg-white dark:bg-slate-900 shadow-2xl overflow-hidden">
        {/* Chat header */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
          <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center shadow-sm">
            <Bot size={18} className="text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-slate-800 dark:text-white">LLM Wiki Assistant</p>
            <p className="text-xs text-emerald-500 flex items-center gap-1">
              <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full inline-block animate-pulse" />
              ออนไลน์
            </p>
          </div>
          <div className="flex gap-1">
            <div className="w-2.5 h-2.5 rounded-full bg-red-400" />
            <div className="w-2.5 h-2.5 rounded-full bg-amber-400" />
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
          </div>
        </div>

        {/* Messages */}
        <div className="p-4 space-y-3">
          <div className="flex justify-end">
            <div className="bg-indigo-600 text-white rounded-2xl rounded-br-sm px-3.5 py-2 text-xs max-w-[200px] leading-relaxed shadow-sm">
              ขั้นตอนการแจ้งสินไหมทดแทนมีอะไรบ้างครับ?
            </div>
          </div>
          <div className="flex justify-start gap-2.5">
            <div className="w-6 h-6 rounded-full bg-indigo-100 dark:bg-indigo-900 flex items-center justify-center flex-shrink-0 mt-0.5">
              <Bot size={12} className="text-indigo-600" />
            </div>
            <div className="bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 rounded-2xl rounded-bl-sm px-3.5 py-2.5 text-xs max-w-[210px] leading-relaxed">
              มีขั้นตอนหลัก 3 ขั้น ครับ<br/>
              <span className="text-indigo-600 dark:text-indigo-400">1.</span> แจ้งอุบัติเหตุภายใน 24 ชม.<br/>
              <span className="text-indigo-600 dark:text-indigo-400">2.</span> รวบรวมเอกสารหลักฐาน<br/>
              <span className="text-indigo-600 dark:text-indigo-400">3.</span> ยื่นคำร้องผ่านแอปหรือสาขา
            </div>
          </div>
          {/* Source ref */}
          <div className="ml-8 flex items-center gap-1.5 text-xs text-slate-400 dark:text-slate-500">
            <BookOpen size={10} />
            <span>Customer Service - Claims</span>
            <span className="text-blue-500 cursor-pointer">[คลิก link]</span>
          </div>
          {/* Typing */}
          <div className="flex justify-end">
            <div className="bg-indigo-600 text-white rounded-2xl rounded-br-sm px-3.5 py-2 text-xs max-w-[200px]">
              ต้องใช้เอกสารอะไรบ้างครับ?
            </div>
          </div>
          <div className="flex items-center gap-1 ml-2">
            {[0, 150, 300].map((d) => (
              <span key={d} className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce"
                style={{ animationDelay: `${d}ms` }} />
            ))}
          </div>
        </div>

        {/* Input bar */}
        <div className="px-4 pb-4">
          <div className="flex gap-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2">
            <span className="text-xs text-slate-400 dark:text-slate-500 flex-1">พิมพ์คำถาม…</span>
            <div className="w-6 h-6 rounded-lg bg-indigo-600 flex items-center justify-center flex-shrink-0">
              <ArrowRight size={12} className="text-white" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Data ──────────────────────────────────────────────────────────────────────
const FEATURES = [
  {
    icon: <Layers size={22} />,
    color: "bg-indigo-100 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400",
    title: "4-Layer Smart Retrieval",
    desc: "ค้นหาคำตอบผ่าน 4 ชั้น: Answer Cache → Canonical QA → Wiki Pages → pgvector ตรวจทุกชั้นก่อนตอบ มั่นใจได้ว่าแม่นยำที่สุด",
  },
  {
    icon: <MessageSquare size={22} />,
    color: "bg-violet-100 dark:bg-violet-950 text-violet-600 dark:text-violet-400",
    title: "AI Chat Assistant",
    desc: "โต้ตอบด้วยภาษาธรรมชาติ รองรับทั้งไทยและอังกฤษ จำบริบทการสนทนาต่อเนื่อง ตอบแบบมีแหล่งอ้างอิงชัดเจน",
  },
  {
    icon: <BookOpen size={22} />,
    color: "bg-blue-100 dark:bg-blue-950 text-blue-600 dark:text-blue-400",
    title: "Wiki Knowledge Base",
    desc: "จัดการเอกสาร นโยบาย และความรู้องค์กรอย่างเป็นระบบ รองรับ Markdown, PDF, Word พร้อม auto-indexing",
  },
  {
    icon: <Zap size={22} />,
    color: "bg-amber-100 dark:bg-amber-950 text-amber-600 dark:text-amber-400",
    title: "Answer Cache & Learning",
    desc: "เรียนรู้จากทุกการสนทนา คำถามที่ถามบ่อยตอบเร็วขึ้น 10 เท่า ลด LLM calls และต้นทุนในระยะยาว",
  },
  {
    icon: <Building2 size={22} />,
    color: "bg-emerald-100 dark:bg-emerald-950 text-emerald-600 dark:text-emerald-400",
    title: "Multi-Company Support",
    desc: "รองรับหลายบริษัทในระบบเดียว แยกข้อมูลอย่างปลอดภัย ทีมต่างสาขาหรือต่างบริษัทในเครือใช้งานร่วมกันได้",
  },
  {
    icon: <Shield size={22} />,
    color: "bg-rose-100 dark:bg-rose-950 text-rose-600 dark:text-rose-400",
    title: "Enterprise Security",
    desc: "ตรวจสอบสิทธิ์ด้วย API Key รองรับ On-premise deployment ข้อมูลไม่ออกนอกองค์กร ปลอดภัยตามมาตรฐาน enterprise",
  },
];

const STEPS = [
  {
    num: "01",
    icon: <FileText size={20} />,
    color: "bg-indigo-600",
    title: "อัปโหลดเอกสาร",
    desc: "นำเข้าเอกสาร PDF, Word, Markdown หรือ URL ของ Wiki ระบบรองรับหลายรูปแบบ ไม่ต้องแปลงไฟล์ก่อน",
  },
  {
    num: "02",
    icon: <Cpu size={20} />,
    color: "bg-violet-600",
    title: "AI ประมวลผลอัตโนมัติ",
    desc: "ระบบแปลงเอกสารเป็น Vector Embeddings สร้าง Index และ Chunking อัตโนมัติ พร้อมให้ค้นหาภายใน 5 นาที",
  },
  {
    num: "03",
    icon: <MessageSquare size={20} />,
    color: "bg-blue-600",
    title: "ถามด้วยภาษาธรรมชาติ",
    desc: "ผู้ใช้งานถามผ่าน Chat Interface เป็นภาษาไทยหรืออังกฤษ ไม่ต้องรู้จักโครงสร้างข้อมูล",
  },
  {
    num: "04",
    icon: <Sparkles size={20} />,
    color: "bg-emerald-600",
    title: "ได้คำตอบทันที",
    desc: "AI ดึงข้อมูลจากฐานความรู้และสังเคราะห์คำตอบ พร้อมแหล่งอ้างอิงที่ตรวจสอบได้ ถูกต้องแม่นยำ",
  },
];

const TIERS = [
  {
    label: "Startup",
    size: "< 50 คน",
    color: "border-slate-200 dark:border-slate-700",
    badge: "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400",
    icon: <Users size={20} className="text-slate-500" />,
    features: [
      "ตั้งค่าได้ภายใน 1 ชั่วโมง",
      "รองรับเอกสารสูงสุด 500 หน้า",
      "Chat + Wiki Knowledge Base",
      "ไม่ต้องใช้ GPU (Cloud LLM)",
      "1 บริษัท / 1 ทีม",
    ],
    cta: "เริ่มต้นง่าย",
    highlight: false,
  },
  {
    label: "SME",
    size: "50 – 500 คน",
    color: "border-indigo-500 dark:border-indigo-500",
    badge: "bg-indigo-600 text-white",
    icon: <TrendingUp size={20} className="text-indigo-600 dark:text-indigo-400" />,
    features: [
      "Multi-department knowledge base",
      "Auto-sync เอกสารใหม่",
      "Canonical QA Editor",
      "Answer Cache & Learning",
      "Session history & context",
      "Analytics dashboard",
    ],
    cta: "ยอดนิยม",
    highlight: true,
  },
  {
    label: "Enterprise",
    size: "500+ คน",
    color: "border-slate-200 dark:border-slate-700",
    badge: "bg-slate-900 dark:bg-slate-700 text-white",
    icon: <Building2 size={20} className="text-slate-500" />,
    features: [
      "Multi-company data isolation",
      "On-premise / Private Cloud",
      "Custom LLM & Embedding models",
      "Audit logs & compliance",
      "SSO / API integration",
      "Dedicated support & SLA",
    ],
    cta: "Enterprise-grade",
    highlight: false,
  },
];

const TECH_STACK = [
  { icon: <Bot size={20} />, name: "Ollama", desc: "Local LLM Server", color: "text-indigo-500" },
  { icon: <Database size={20} />, name: "Supabase", desc: "PostgreSQL + pgvector", color: "text-emerald-500" },
  { icon: <Code2 size={20} />, name: "FastAPI", desc: "Python Backend", color: "text-blue-500" },
  { icon: <Globe size={20} />, name: "Next.js", desc: "React Frontend", color: "text-slate-700 dark:text-slate-300" },
  { icon: <HardDrive size={20} />, name: "pgvector", desc: "Vector Similarity Search", color: "text-violet-500" },
  { icon: <GitBranch size={20} />, name: "RAG Pipeline", desc: "Retrieval-Augmented Generation", color: "text-amber-500" },
];

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white dark:bg-slate-950 text-slate-900 dark:text-white antialiased">
      <LandingNav />

      {/* ── HERO ──────────────────────────────────────────────────────────── */}
      <section className="relative min-h-screen flex items-center overflow-hidden pt-16">
        {/* Background gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-white to-indigo-50 dark:from-slate-950 dark:via-slate-950 dark:to-indigo-950/50" />

        {/* Blur blobs */}
        <div className="absolute top-1/4 left-10 w-72 h-72 bg-indigo-400/20 dark:bg-indigo-600/20 rounded-full blur-3xl animate-float-slow pointer-events-none" />
        <div className="absolute bottom-1/4 right-10 w-96 h-96 bg-violet-400/15 dark:bg-violet-600/20 rounded-full blur-3xl animate-float pointer-events-none" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-blue-300/10 dark:bg-blue-700/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 w-full">
          <div className="grid lg:grid-cols-2 gap-12 lg:gap-20 items-center py-16 lg:py-20">
            {/* Left: Text */}
            <div className="text-center lg:text-left">
              {/* Badge */}
              <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-indigo-200 dark:border-indigo-800 bg-indigo-50 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 text-xs font-semibold mb-6 shadow-sm">
                <Sparkles size={12} />
                AI-Powered Enterprise Knowledge Base
              </div>

              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold leading-tight mb-6 tracking-tight">
                <span className="text-slate-900 dark:text-white">ระบบฐานความรู้</span>
                <br />
                <span className="bg-clip-text text-transparent bg-gradient-to-r from-indigo-500 via-purple-500 to-blue-500">
                  อัจฉริยะสำหรับ
                </span>
                <br />
                <span className="text-slate-900 dark:text-white">องค์กรยุคใหม่</span>
              </h1>

              <p className="text-lg sm:text-xl text-slate-600 dark:text-slate-400 leading-relaxed mb-8 max-w-lg mx-auto lg:mx-0">
                เปลี่ยนเอกสาร นโยบาย และความรู้ขององค์กรให้กลายเป็น{" "}
                <strong className="text-slate-800 dark:text-slate-200">AI Assistant</strong>{" "}
                ที่ตอบคำถามพนักงานได้ทันทีด้วย <strong className="text-slate-800 dark:text-slate-200">LLM + RAG Technology</strong>
              </p>

              <div className="flex flex-col sm:flex-row gap-3 justify-center lg:justify-start">
                <Link href="/login"
                  className="inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl
                             bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm
                             shadow-lg shadow-indigo-600/30 hover:shadow-indigo-600/50 transition-all duration-200 hover:-translate-y-0.5">
                  <Sparkles size={16} />
                  เริ่มต้นใช้งานฟรี
                  <ArrowRight size={14} />
                </Link>
                <a href="#features"
                  className="inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl
                             border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900
                             hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300
                             font-semibold text-sm transition-all duration-200 hover:-translate-y-0.5">
                  ดูฟีเจอร์ทั้งหมด
                  <ChevronRight size={14} />
                </a>
              </div>

              {/* Mini trust indicators */}
              <div className="flex flex-wrap gap-x-5 gap-y-2 mt-8 justify-center lg:justify-start text-xs text-slate-500 dark:text-slate-500">
                {["4-Layer RAG Architecture", "รองรับภาษาไทย 100%", "On-premise พร้อมใช้"].map((t) => (
                  <span key={t} className="flex items-center gap-1.5">
                    <CheckCircle size={13} className="text-emerald-500 flex-shrink-0" />
                    {t}
                  </span>
                ))}
              </div>
            </div>

            {/* Right: Mock Chat */}
            <div className="flex justify-center lg:justify-end">
              <MockChat />
            </div>
          </div>
        </div>

        {/* Wave separator */}
        <div className="absolute bottom-0 left-0 right-0">
          <svg viewBox="0 0 1440 60" className="w-full fill-indigo-600 dark:fill-indigo-900/80" preserveAspectRatio="none" style={{ height: 48 }}>
            <path d="M0,32 C240,60 480,0 720,30 C960,60 1200,0 1440,32 L1440,60 L0,60 Z" />
          </svg>
        </div>
      </section>

      {/* ── STATS BAR ─────────────────────────────────────────────────────── */}
      <section className="bg-indigo-600 dark:bg-indigo-900/80 py-10">
        <div className="mx-auto max-w-6xl px-4 grid grid-cols-2 md:grid-cols-4 gap-6 text-center text-white">
          {[
            { value: "4", unit: "Layer", label: "RAG Architecture" },
            { value: "<1s", unit: "", label: "Response Time" },
            { value: "∞", unit: "", label: "รองรับหลายบริษัท" },
            { value: "100%", unit: "", label: "On-premise พร้อมใช้" },
          ].map((s) => (
            <div key={s.label} className="flex flex-col items-center gap-1">
              <div className="text-3xl sm:text-4xl font-extrabold text-white">
                {s.value}<span className="text-xl text-indigo-300">{s.unit}</span>
              </div>
              <div className="text-xs text-indigo-200 font-medium">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── FEATURES ──────────────────────────────────────────────────────── */}
      <section id="features" className="py-24 px-4">
        <div className="mx-auto max-w-7xl">
          {/* Header */}
          <div className="text-center mb-16">
            <span className="inline-block px-3 py-1 rounded-full text-xs font-semibold bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 mb-4">
              ✦ ฟีเจอร์หลัก
            </span>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white mb-4">
              ครบครัน ทรงพลัง ใช้งานได้จริง
            </h2>
            <p className="text-lg text-slate-500 dark:text-slate-400 max-w-2xl mx-auto">
              ออกแบบมาสำหรับองค์กรที่ต้องการความแม่นยำ ความเร็ว และความปลอดภัยในการจัดการความรู้
            </p>
          </div>

          {/* 3×2 grid */}
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {FEATURES.map((f) => (
              <div key={f.title}
                className="group relative rounded-2xl border border-slate-200 dark:border-slate-800
                           bg-white dark:bg-slate-900 p-6
                           hover:border-indigo-300 dark:hover:border-indigo-700
                           hover:shadow-xl hover:shadow-indigo-100 dark:hover:shadow-indigo-950
                           transition-all duration-300 hover:-translate-y-1">
                <div className={`w-11 h-11 rounded-xl flex items-center justify-center mb-4 ${f.color}`}>
                  {f.icon}
                </div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white mb-2">{f.title}</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">{f.desc}</p>
                <div className="absolute bottom-0 left-0 right-0 h-0.5 rounded-b-2xl bg-gradient-to-r from-indigo-500 to-purple-500 scale-x-0 group-hover:scale-x-100 transition-transform duration-300 origin-left" />
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS ──────────────────────────────────────────────────── */}
      <section id="how-it-works" className="py-24 px-4 bg-slate-50 dark:bg-slate-900/50">
        <div className="mx-auto max-w-5xl">
          <div className="text-center mb-16">
            <span className="inline-block px-3 py-1 rounded-full text-xs font-semibold bg-violet-100 dark:bg-violet-950 text-violet-700 dark:text-violet-300 mb-4">
              ✦ ขั้นตอนการทำงาน
            </span>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white mb-4">
              เริ่มใช้งานได้ใน 4 ขั้นตอน
            </h2>
            <p className="text-lg text-slate-500 dark:text-slate-400">
              ไม่ต้องเขียนโค้ด ไม่ต้องมีทีม Data Scientist ตั้งค่าได้เองในเวลาไม่กี่ชั่วโมง
            </p>
          </div>

          {/* Steps */}
          <div className="grid md:grid-cols-4 gap-6 relative">
            {/* Connector line */}
            <div className="hidden md:block absolute top-10 left-[calc(12.5%+1.5rem)] right-[calc(12.5%+1.5rem)] h-0.5 bg-gradient-to-r from-indigo-300 via-violet-300 to-emerald-300 dark:from-indigo-700 dark:via-violet-700 dark:to-emerald-700" />

            {STEPS.map((s, i) => (
              <div key={i} className="relative flex flex-col items-center text-center group">
                {/* Circle */}
                <div className={`relative z-10 w-20 h-20 rounded-2xl ${s.color} flex flex-col items-center justify-center shadow-lg mb-5
                                  group-hover:scale-110 transition-transform duration-200`}>
                  <span className="text-white/70 text-xs font-bold leading-none">{s.num}</span>
                  <span className="text-white mt-0.5">{s.icon}</span>
                </div>
                <h3 className="text-sm font-bold text-slate-800 dark:text-white mb-2">{s.title}</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>

          {/* RAG architecture detail */}
          <div className="mt-16 rounded-2xl border border-indigo-200 dark:border-indigo-800 bg-indigo-50 dark:bg-indigo-950/40 p-6">
            <p className="text-center text-xs font-semibold text-indigo-700 dark:text-indigo-300 uppercase tracking-wider mb-4">
              4-Layer Retrieval Architecture
            </p>
            <div className="flex flex-wrap justify-center items-center gap-2 text-xs">
              {[
                { label: "Answer Cache", color: "bg-emerald-100 dark:bg-emerald-900 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800" },
                { label: "→", color: "text-slate-400 font-bold" },
                { label: "Canonical QA", color: "bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-800" },
                { label: "→", color: "text-slate-400 font-bold" },
                { label: "Wiki Pages", color: "bg-violet-100 dark:bg-violet-900 text-violet-700 dark:text-violet-300 border-violet-200 dark:border-violet-800" },
                { label: "→", color: "text-slate-400 font-bold" },
                { label: "Vector Chunks", color: "bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300 border-indigo-200 dark:border-indigo-800" },
                { label: "→", color: "text-slate-400 font-bold" },
                { label: "LLM Generate ✨", color: "bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800" },
              ].map((item, i) =>
                item.label === "→" ? (
                  <span key={i} className="hidden sm:block text-slate-400 font-bold text-sm">→</span>
                ) : (
                  <span key={i} className={`px-3 py-1.5 rounded-lg border font-medium ${item.color}`}>
                    {item.label}
                  </span>
                )
              )}
            </div>
            <p className="text-center text-xs text-slate-500 dark:text-slate-500 mt-4">
              ตรวจทุกชั้นตามลำดับ คืน cache ก่อนถ้ามี — ลด latency และต้นทุน LLM calls
            </p>
          </div>
        </div>
      </section>

      {/* ── SCALE TIERS ───────────────────────────────────────────────────── */}
      <section id="scale" className="py-24 px-4">
        <div className="mx-auto max-w-6xl">
          <div className="text-center mb-16">
            <span className="inline-block px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 mb-4">
              ✦ ขนาดองค์กร
            </span>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white mb-4">
              เหมาะสำหรับทุกขนาดองค์กร
            </h2>
            <p className="text-lg text-slate-500 dark:text-slate-400">
              ตั้งแต่ Startup ไปจนถึง Enterprise ระดับพันคน ปรับขนาดได้ตามการเติบโต
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {TIERS.map((tier) => (
              <div key={tier.label}
                className={`relative rounded-2xl border-2 ${tier.color} p-7
                            ${tier.highlight
                              ? "bg-white dark:bg-slate-900 shadow-2xl shadow-indigo-100 dark:shadow-indigo-950 scale-105"
                              : "bg-white dark:bg-slate-900 hover:shadow-lg"
                            } transition-all duration-300`}>
                {tier.highlight && (
                  <div className="absolute -top-3.5 left-1/2 -translate-x-1/2">
                    <span className="px-3 py-1 rounded-full bg-indigo-600 text-white text-xs font-bold shadow-lg shadow-indigo-600/40">
                      ยอดนิยม
                    </span>
                  </div>
                )}

                {/* Tier header */}
                <div className="flex items-center gap-3 mb-1">
                  {tier.icon}
                  <h3 className="text-xl font-extrabold text-slate-900 dark:text-white">{tier.label}</h3>
                </div>
                <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">{tier.size}</p>

                {/* Features */}
                <ul className="space-y-2.5 mb-8">
                  {tier.features.map((f) => (
                    <li key={f} className="flex items-start gap-2.5 text-sm text-slate-700 dark:text-slate-300">
                      <CheckCircle size={15} className={tier.highlight ? "text-indigo-500 flex-shrink-0 mt-0.5" : "text-emerald-500 flex-shrink-0 mt-0.5"} />
                      {f}
                    </li>
                  ))}
                </ul>

                <Link href="/login"
                  className={`block text-center py-2.5 rounded-xl text-sm font-semibold transition-colors
                    ${tier.highlight
                      ? "bg-indigo-600 hover:bg-indigo-700 text-white shadow-md shadow-indigo-600/30"
                      : "border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300"
                    }`}>
                  เริ่มต้นเลย →
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── TECH STACK ────────────────────────────────────────────────────── */}
      <section id="tech" className="py-24 px-4 bg-slate-50 dark:bg-slate-900/50">
        <div className="mx-auto max-w-5xl">
          <div className="text-center mb-14">
            <span className="inline-block px-3 py-1 rounded-full text-xs font-semibold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 mb-4">
              ✦ เทคโนโลยีที่ใช้
            </span>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white mb-4">
              Built on Open & Battle-tested Technology
            </h2>
            <p className="text-lg text-slate-500 dark:text-slate-400">
              ไม่ Lock-in กับ vendor ใด รองรับ LLM ทั้งแบบ Cloud และ On-premise
            </p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            {TECH_STACK.map((t) => (
              <div key={t.name}
                className="flex items-center gap-4 rounded-xl border border-slate-200 dark:border-slate-800
                           bg-white dark:bg-slate-900 px-5 py-4
                           hover:border-indigo-300 dark:hover:border-indigo-700
                           hover:shadow-md transition-all duration-200 group">
                <div className={`${t.color} group-hover:scale-110 transition-transform duration-200 flex-shrink-0`}>
                  {t.icon}
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-bold text-slate-900 dark:text-white">{t.name}</p>
                  <p className="text-xs text-slate-400 dark:text-slate-500 truncate">{t.desc}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Compatible note */}
          <p className="text-center text-sm text-slate-500 dark:text-slate-500 mt-8">
            รองรับ OpenAI-compatible API · LLaMA · Qwen · Mistral · DeepSeek และอื่น ๆ
          </p>
        </div>
      </section>

      {/* ── FINAL CTA ─────────────────────────────────────────────────────── */}
      <section className="py-24 px-4 relative overflow-hidden">
        {/* Background */}
        <div className="absolute inset-0 bg-gradient-to-br from-indigo-600 via-indigo-700 to-violet-700" />
        <div className="absolute top-0 left-1/4 w-64 h-64 bg-white/10 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-violet-500/20 rounded-full blur-3xl" />

        <div className="relative z-10 mx-auto max-w-3xl text-center text-white">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-white/30 bg-white/10 text-xs font-semibold mb-6">
            <Sparkles size={12} />
            พร้อมเริ่มต้นแล้วหรือยัง?
          </div>
          <h2 className="text-4xl sm:text-5xl font-extrabold mb-6 leading-tight">
            เปลี่ยนความรู้ขององค์กร
            <br />
            ให้เป็น AI ทำงานให้คุณ
          </h2>
          <p className="text-lg text-indigo-200 mb-10 max-w-xl mx-auto leading-relaxed">
            เริ่มต้นได้วันนี้ ไม่ต้องใช้บัตรเครดิต ไม่ต้องมีทีม DevOps
            ตั้งค่าเสร็จภายใน 1 ชั่วโมง
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link href="/login"
              className="inline-flex items-center justify-center gap-2 px-8 py-4 rounded-xl
                         bg-white text-indigo-700 hover:bg-indigo-50
                         text-base font-bold shadow-xl hover:shadow-2xl transition-all duration-200 hover:-translate-y-0.5">
              <Sparkles size={18} />
              เริ่มใช้งานฟรีเลย
              <ArrowRight size={16} />
            </Link>
            <a href="#features"
              className="inline-flex items-center justify-center gap-2 px-8 py-4 rounded-xl
                         border border-white/40 bg-white/10 hover:bg-white/20
                         text-white text-base font-semibold transition-all duration-200">
              ดูฟีเจอร์ทั้งหมด
            </a>
          </div>

          {/* Mini stats */}
          <div className="flex flex-wrap justify-center gap-8 mt-12 text-sm text-indigo-200">
            {["ติดตั้งในองค์กรไทยแล้ว", "รองรับ 100% ภาษาไทย", "On-premise เต็มรูปแบบ"].map((t) => (
              <span key={t} className="flex items-center gap-2">
                <CheckCircle size={15} className="text-indigo-300" />
                {t}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── FOOTER ────────────────────────────────────────────────────────── */}
      <footer className="border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 py-10 px-4">
        <div className="mx-auto max-w-7xl">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            {/* Logo */}
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center">
                <Brain size={15} className="text-white" />
              </div>
              <span className="text-sm font-bold text-slate-800 dark:text-white">Enterprise LLM Wiki</span>
            </div>

            {/* Links */}
            <div className="flex flex-wrap items-center gap-5 text-xs text-slate-500 dark:text-slate-500">
              <a href="#features" className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">ฟีเจอร์</a>
              <a href="#how-it-works" className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">ขั้นตอน</a>
              <a href="#scale" className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">ขนาดองค์กร</a>
              <a href="#tech" className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">เทคโนโลยี</a>
              <Link href="/login" className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 font-medium transition-colors">เข้าสู่ระบบ</Link>
            </div>

            {/* Version */}
            <p className="text-xs text-slate-400 dark:text-slate-600">
              v0.2.0 · Powered by Ollama + Supabase
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
