"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import { Settings, Save, RefreshCw, Plus, X, ChevronDown, ChevronUp, Info } from "lucide-react";

const COMPANY_CODE = process.env.NEXT_PUBLIC_COMPANY_CODE || "DEVES";

// ── Types ─────────────────────────────────────────────────────────────────────
interface BotSettings {
  no_answer_phrases:    string[];
  clarify_phrases:      string[];
  ambiguous_keywords:   Record<string, string[]>;
  clear_question_words: string[];
}

type SettingKey = keyof BotSettings;

// ── Metadata for each setting ─────────────────────────────────────────────────
const SETTING_META: Record<SettingKey, { label: string; description: string; icon: string }> = {
  no_answer_phrases: {
    label: "วลีที่บอกว่า 'ไม่มีข้อมูล'",
    description: "ถ้าคำตอบของบอทมีวลีเหล่านี้ → นับเป็น 'ตอบไม่ได้' แล้วบันทึกลง Missed Q",
    icon: "❌",
  },
  clarify_phrases: {
    label: "วลีที่บอกว่า 'กำลังถามกลับ'",
    description: "ถ้าคำตอบมีวลีเหล่านี้ → ไม่นับเป็น 'ตอบไม่ได้' (บทสนทนายังไม่จบ)",
    icon: "❓",
  },
  ambiguous_keywords: {
    label: "คำกว้าง → ตัวเลือก",
    description: "ถ้าคำถามมีคำเหล่านี้โดยไม่มีบริบท บอทจะถามกลับพร้อมตัวเลือก",
    icon: "🔀",
  },
  clear_question_words: {
    label: "คำถามชัดเจน (ข้ามการถามกลับ)",
    description: "คำที่บ่งบอกว่าผู้ใช้ถามชัดเจน แม้จะมีคำกว้างก็ตอบตรงเลย",
    icon: "✅",
  },
};

// ── Simple List Editor ────────────────────────────────────────────────────────
function ListEditor({
  items,
  onChange,
}: {
  items: string[];
  onChange: (v: string[]) => void;
}) {
  const [newItem, setNewItem] = useState("");

  function add() {
    const trimmed = newItem.trim();
    if (!trimmed || items.includes(trimmed)) return;
    onChange([...items, trimmed]);
    setNewItem("");
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1.5">
        {items.map((item) => (
          <span
            key={item}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium
                       bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300
                       border border-slate-200 dark:border-slate-700"
          >
            {item}
            <button
              onClick={() => onChange(items.filter((x) => x !== item))}
              className="text-slate-400 hover:text-red-500 transition-colors"
            >
              <X size={11} />
            </button>
          </span>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          value={newItem}
          onChange={(e) => setNewItem(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && add()}
          placeholder="พิมพ์แล้วกด Enter หรือ +"
          className="flex-1 text-sm rounded-lg border border-slate-200 dark:border-slate-700
                     bg-white dark:bg-slate-800 px-3 py-1.5 text-slate-900 dark:text-white
                     focus:outline-none focus:ring-2 focus:ring-indigo-500 placeholder-slate-400"
        />
        <button
          onClick={add}
          className="px-3 py-1.5 rounded-lg bg-indigo-600 text-white text-sm hover:bg-indigo-700 transition-colors"
        >
          <Plus size={14} />
        </button>
      </div>
    </div>
  );
}

// ── Ambiguous Keywords Editor ─────────────────────────────────────────────────
function AmbiguousKeywordsEditor({
  value,
  onChange,
}: {
  value: Record<string, string[]>;
  onChange: (v: Record<string, string[]>) => void;
}) {
  const [newKey, setNewKey]   = useState("");
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  function addKeyword() {
    const k = newKey.trim();
    if (!k || k in value) return;
    onChange({ ...value, [k]: [] });
    setExpanded((e) => ({ ...e, [k]: true }));
    setNewKey("");
  }

  function removeKeyword(k: string) {
    const next = { ...value };
    delete next[k];
    onChange(next);
  }

  function updateChoices(k: string, choices: string[]) {
    onChange({ ...value, [k]: choices });
  }

  return (
    <div className="space-y-2">
      {Object.entries(value).map(([kw, choices]) => (
        <div
          key={kw}
          className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden"
        >
          {/* Keyword header */}
          <div className="flex items-center gap-2 px-3 py-2 bg-slate-50 dark:bg-slate-800/60">
            <button
              onClick={() => setExpanded((e) => ({ ...e, [kw]: !e[kw] }))}
              className="flex items-center gap-1.5 flex-1 text-left"
            >
              {expanded[kw] ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
              <span className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                {kw}
              </span>
              <span className="text-xs text-slate-400 dark:text-slate-500">
                ({choices.length} ตัวเลือก)
              </span>
            </button>
            <button
              onClick={() => removeKeyword(kw)}
              className="text-slate-400 hover:text-red-500 transition-colors"
            >
              <X size={14} />
            </button>
          </div>

          {/* Choices list */}
          {expanded[kw] && (
            <div className="px-3 py-2 bg-white dark:bg-slate-900/40">
              <ListEditor items={choices} onChange={(c) => updateChoices(kw, c)} />
            </div>
          )}
        </div>
      ))}

      {/* Add new keyword */}
      <div className="flex gap-2">
        <input
          value={newKey}
          onChange={(e) => setNewKey(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && addKeyword()}
          placeholder="เพิ่มคำกว้างใหม่ เช่น สาขา"
          className="flex-1 text-sm rounded-lg border border-slate-200 dark:border-slate-700
                     bg-white dark:bg-slate-800 px-3 py-1.5 text-slate-900 dark:text-white
                     focus:outline-none focus:ring-2 focus:ring-indigo-500 placeholder-slate-400"
        />
        <button
          onClick={addKeyword}
          className="px-3 py-1.5 rounded-lg bg-indigo-600 text-white text-sm hover:bg-indigo-700 transition-colors"
        >
          <Plus size={14} />
        </button>
      </div>
    </div>
  );
}

// ── Setting Card ──────────────────────────────────────────────────────────────
function SettingCard({
  settingKey,
  meta,
  value,
  onChange,
  onSave,
  saving,
  dirty,
}: {
  settingKey: SettingKey;
  meta: (typeof SETTING_META)[SettingKey];
  value: BotSettings[SettingKey];
  onChange: (v: BotSettings[SettingKey]) => void;
  onSave: () => void;
  saving: boolean;
  dirty: boolean;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 px-5 py-4 border-b border-slate-100 dark:border-slate-800">
        <div className="flex items-center gap-2.5">
          <span className="text-xl">{meta.icon}</span>
          <div>
            <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">{meta.label}</p>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 flex items-center gap-1">
              <Info size={11} className="shrink-0" />
              {meta.description}
            </p>
          </div>
        </div>
        <button
          onClick={onSave}
          disabled={saving || !dirty}
          className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold
                     bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-40 transition-colors"
        >
          {saving ? <RefreshCw size={12} className="animate-spin" /> : <Save size={12} />}
          บันทึก
        </button>
      </div>

      {/* Editor */}
      <div className="px-5 py-4">
        {settingKey === "ambiguous_keywords" ? (
          <AmbiguousKeywordsEditor
            value={value as Record<string, string[]>}
            onChange={onChange as (v: Record<string, string[]>) => void}
          />
        ) : (
          <ListEditor
            items={value as string[]}
            onChange={onChange as (v: string[]) => void}
          />
        )}
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function SettingsPage() {
  const [settings, setSettings]   = useState<BotSettings | null>(null);
  const [original, setOriginal]   = useState<BotSettings | null>(null);
  const [loading, setLoading]     = useState(true);
  const [savingKey, setSavingKey] = useState<SettingKey | null>(null);
  const [toast, setToast]         = useState<string | null>(null);
  const [error, setError]         = useState<string | null>(null);

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  }

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch(`/api/bot-settings?company_code=${COMPANY_CODE}`);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setSettings(data.settings);
      setOriginal(JSON.parse(JSON.stringify(data.settings)));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "โหลดข้อมูลไม่ได้");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  function handleChange(key: SettingKey, value: BotSettings[SettingKey]) {
    setSettings((s) => s ? { ...s, [key]: value } : s);
  }

  async function handleSave(key: SettingKey) {
    if (!settings) return;
    setSavingKey(key);
    try {
      const res = await apiFetch("/api/bot-settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          company_code: COMPANY_CODE,
          key,
          value: settings[key],
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      setOriginal((o) => o ? { ...o, [key]: JSON.parse(JSON.stringify(settings[key])) } : o);
      showToast(`✅ บันทึก "${SETTING_META[key].label}" สำเร็จ`);
    } catch (e: unknown) {
      showToast(`❌ ${e instanceof Error ? e.message : "บันทึกไม่สำเร็จ"}`);
    } finally {
      setSavingKey(null);
    }
  }

  function isDirty(key: SettingKey): boolean {
    if (!settings || !original) return false;
    return JSON.stringify(settings[key]) !== JSON.stringify(original[key]);
  }

  // ── Render ────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400 dark:text-slate-600 text-sm gap-2">
        <RefreshCw size={16} className="animate-spin" />
        กำลังโหลด…
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3 text-slate-500 dark:text-slate-400">
        <p className="text-sm text-red-500">{error}</p>
        <button
          onClick={load}
          className="text-xs px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
        >
          ลองใหม่
        </button>
      </div>
    );
  }

  if (!settings) return null;

  return (
    <div className="max-w-3xl mx-auto py-2">
      {/* Page header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-indigo-100 dark:bg-indigo-900/40 flex items-center justify-center">
            <Settings size={18} className="text-indigo-600 dark:text-indigo-400" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-800 dark:text-slate-100">Bot Settings</h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {COMPANY_CODE} · แก้ไขแล้วบันทึก — ระบบโหลดค่าใหม่ทันที
            </p>
          </div>
        </div>
        <button
          onClick={load}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
                     text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-800
                     hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
        >
          <RefreshCw size={13} />
          รีโหลด
        </button>
      </div>

      {/* Setting cards */}
      <div className="space-y-5">
        {(Object.keys(SETTING_META) as SettingKey[]).map((key) => (
          <SettingCard
            key={key}
            settingKey={key}
            meta={SETTING_META[key]}
            value={settings[key]}
            onChange={(v) => handleChange(key, v)}
            onSave={() => handleSave(key)}
            saving={savingKey === key}
            dirty={isDirty(key)}
          />
        ))}
      </div>

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 px-4 py-2.5 rounded-xl bg-slate-900 dark:bg-slate-100
                        text-white dark:text-slate-900 text-sm font-medium shadow-xl
                        animate-in fade-in slide-in-from-bottom-2 duration-200">
          {toast}
        </div>
      )}
    </div>
  );
}
