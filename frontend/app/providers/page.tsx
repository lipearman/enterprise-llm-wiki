"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import {
  Cpu, Plus, Trash2, Pencil, X, Check, Zap, AlertCircle,
  ArrowUp, ArrowDown, Server, RefreshCw,
} from "lucide-react";

const inputCls =
  "rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 " +
  "text-slate-800 dark:text-slate-200 placeholder-slate-400 px-3 py-2 text-sm " +
  "focus:outline-none focus:ring-2 focus:ring-indigo-500";

const ROLE_LABELS: Record<string, string> = {
  answer_llm:      "💬 Answer LLM (คำตอบ chat)",
  chat:            "🗨️ Chat (ทั่วไป)",
  fact_extraction: "🧠 Fact Extraction (ingest)",
  wiki_generation: "📖 Wiki Generation (ingest)",
  canonical_qa:    "❓ Canonical QA matching",
  embed:           "🔢 Embeddings",
};

interface Provider {
  id: string; name: string; base_url: string; protocol: string;
  is_active: boolean; api_key_masked: string; has_key: boolean;
}
interface Assignment {
  id: string; role: string; provider_id: string; provider_name: string;
  model: string; priority: number; is_active: boolean;
}
interface ModelOpt { id: string; name: string; free: boolean; }

// ── Provider edit modal ───────────────────────────────────────────────────────
function ProviderModal({ initial, onClose, onSaved }: {
  initial: Provider | null; onClose: () => void; onSaved: () => void;
}) {
  const [name, setName]       = useState(initial?.name ?? "");
  const [baseUrl, setBaseUrl] = useState(initial?.base_url ?? "");
  const [apiKey, setApiKey]   = useState("");
  const [active, setActive]   = useState(initial?.is_active ?? true);
  const [err, setErr]         = useState<string | null>(null);
  const [saving, setSaving]   = useState(false);

  const save = async () => {
    setErr(null); setSaving(true);
    try {
      const body = { name, base_url: baseUrl, api_key: apiKey || undefined, protocol: "openai", is_active: active };
      const res = await apiFetch(initial ? `/api/providers/${initial.id}` : "/api/providers", {
        method: initial ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error((await res.json()).detail || `HTTP ${res.status}`);
      onSaved();
    } catch (e) { setErr((e as Error).message); } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div className="w-full max-w-md rounded-2xl bg-white dark:bg-slate-900 shadow-2xl p-5 space-y-3" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-slate-800 dark:text-white">{initial ? "แก้ไข Provider" : "เพิ่ม Provider"}</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600"><X size={18} /></button>
        </div>
        <div className="space-y-2">
          <input className={`${inputCls} w-full`} placeholder="ชื่อ (เช่น sambanova)" value={name} onChange={e => setName(e.target.value)} />
          <input className={`${inputCls} w-full`} placeholder="Base URL (เช่น https://api.sambanova.ai/v1)" value={baseUrl} onChange={e => setBaseUrl(e.target.value)} />
          <input className={`${inputCls} w-full`} type="password"
            placeholder={initial ? "API key (เว้นว่าง = คงเดิม)" : "API key"} value={apiKey} onChange={e => setApiKey(e.target.value)} />
          <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
            <input type="checkbox" checked={active} onChange={e => setActive(e.target.checked)} /> เปิดใช้งาน
          </label>
        </div>
        {err && <div className="text-xs text-red-600 flex items-center gap-1"><AlertCircle size={12} />{err}</div>}
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-3 py-2 rounded-xl text-sm text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800">ยกเลิก</button>
          <button onClick={save} disabled={saving || !name || !baseUrl}
            className="px-4 py-2 rounded-xl text-sm bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-40">
            {saving ? "กำลังบันทึก…" : "บันทึก"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function ProvidersPage() {
  const [providers, setProviders]   = useState<Provider[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [roles, setRoles]           = useState<string[]>([]);
  const [loading, setLoading]       = useState(true);
  const [modal, setModal]           = useState<{ open: boolean; provider: Provider | null }>({ open: false, provider: null });
  const [testResult, setTestResult] = useState<Record<string, string>>({});
  // per-provider-card test model dropdown
  const [cardModels, setCardModels] = useState<Record<string, ModelOpt[]>>({});
  const [cardLoading, setCardLoading] = useState<Record<string, boolean>>({});
  const [cardSel, setCardSel]       = useState<Record<string, string>>({});
  // new assignment form per role
  const [addRow, setAddRow]         = useState<{ role: string; provider_id: string; model: string } | null>(null);
  // model dropdown state for the add-assignment form
  const [modelOpts, setModelOpts]   = useState<ModelOpt[]>([]);
  const [modelLoading, setModelLoading] = useState(false);
  const [modelErr, setModelErr]     = useState<string | null>(null);
  const [freeOnly, setFreeOnly]     = useState(true);
  const [customModel, setCustomModel] = useState(false);

  const loadCardModels = useCallback(async (providerId: string) => {
    if (cardModels[providerId] || cardLoading[providerId]) return;
    setCardLoading(s => ({ ...s, [providerId]: true }));
    try {
      const r = await apiFetch(`/api/providers/${providerId}/models?free_only=true`).then(r => r.json());
      setCardModels(s => ({ ...s, [providerId]: r.ok ? (r.items ?? []) : [] }));
    } catch { setCardModels(s => ({ ...s, [providerId]: [] })); }
    finally { setCardLoading(s => ({ ...s, [providerId]: false })); }
  }, [cardModels, cardLoading]);

  const fetchModels = useCallback(async (providerId: string, free: boolean) => {
    if (!providerId) { setModelOpts([]); return; }
    setModelLoading(true); setModelErr(null);
    try {
      const r = await apiFetch(`/api/providers/${providerId}/models?free_only=${free}`).then(r => r.json());
      if (r.ok) setModelOpts(r.items ?? []);
      else { setModelOpts([]); setModelErr(r.detail ?? `HTTP ${r.status}`); }
    } catch (e) { setModelOpts([]); setModelErr((e as Error).message); }
    finally { setModelLoading(false); }
  }, []);

  // refetch model list whenever the chosen provider or free-toggle changes
  useEffect(() => {
    if (addRow?.provider_id) fetchModels(addRow.provider_id, freeOnly);
  }, [addRow?.provider_id, freeOnly, fetchModels]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [p, a] = await Promise.all([
        apiFetch("/api/providers").then(r => r.json()),
        apiFetch("/api/providers/roles").then(r => r.json()),
      ]);
      setProviders(p.items ?? []);
      setRoles(p.roles ?? []);
      setAssignments(a.items ?? []);
    } finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const delProvider = async (id: string) => {
    if (!confirm("ลบ provider นี้?")) return;
    await apiFetch(`/api/providers/${id}`, { method: "DELETE" });
    load();
  };
  const testProvider = async (id: string, model: string) => {
    setTestResult(t => ({ ...t, [id]: "…" }));
    const r = await apiFetch(`/api/providers/${id}/test${model ? `?model=${encodeURIComponent(model)}` : ""}`, { method: "POST" }).then(r => r.json());
    setTestResult(t => ({
      ...t,
      [id]: r.ok
        ? `✅ ${r.latency}s · ${r.model ?? ""} → ${r.sample ?? ""}`
        : `❌ ${r.model ? r.model + " · " : ""}${r.detail ?? r.status}`,
    }));
  };

  const addAssignment = async (role: string, provider_id: string, model: string, priority: number) => {
    await apiFetch("/api/providers/roles", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role, provider_id, model, priority, is_active: true }),
    });
    setAddRow(null); load();
  };
  const updateAssignment = async (a: Assignment, patch: Partial<Assignment>) => {
    await apiFetch(`/api/providers/roles/${a.id}`, {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...a, ...patch }),
    });
    load();
  };
  const delAssignment = async (id: string) => {
    await apiFetch(`/api/providers/roles/${id}`, { method: "DELETE" });
    load();
  };

  const reorder = (a: Assignment, dir: -1 | 1) => updateAssignment(a, { priority: Math.max(0, a.priority + dir * 10) });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center shadow-sm shadow-indigo-600/40">
            <Cpu size={18} className="text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-900 dark:text-white leading-none">AI Providers</h1>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">จัดการ provider + กำหนดต่อ role + failover อัตโนมัติเมื่อ rate-limit</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={load} className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800">
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} /> รีเฟรช
          </button>
          <button onClick={() => setModal({ open: true, provider: null })} className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-indigo-600 text-white text-sm hover:bg-indigo-700">
            <Plus size={14} /> เพิ่ม Provider
          </button>
        </div>
      </div>

      {/* Providers */}
      <div>
        <h2 className="text-sm font-bold text-slate-700 dark:text-slate-300 mb-2 flex items-center gap-1.5"><Server size={14} /> Providers</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {providers.map(p => (
            <div key={p.id} className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-slate-800 dark:text-white">{p.name}</span>
                    <span className={`w-2 h-2 rounded-full ${p.is_active ? "bg-emerald-500" : "bg-slate-400"}`} />
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5 break-all">{p.base_url}</p>
                  <p className="text-[11px] text-slate-400 font-mono mt-0.5">key {p.api_key_masked}</p>
                </div>
                <div className="flex gap-1">
                  <button onClick={() => setModal({ open: true, provider: p })} className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"><Pencil size={13} /></button>
                  <button onClick={() => delProvider(p.id)} className="p-1.5 rounded-lg text-red-400 hover:bg-red-50 dark:hover:bg-red-950/30"><Trash2 size={13} /></button>
                </div>
              </div>
              <div className="flex items-center gap-2 mt-2">
                <button onClick={() => testProvider(p.id, cardSel[p.id] ?? "")} className="flex items-center gap-1 px-2 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 text-xs text-slate-600 dark:text-slate-300 hover:bg-slate-200 shrink-0">
                  <Zap size={11} /> test
                </button>
                <select
                  className={`${inputCls} text-xs py-1 max-w-[180px]`}
                  value={cardSel[p.id] ?? ""}
                  onFocus={() => loadCardModels(p.id)}
                  onChange={e => setCardSel(s => ({ ...s, [p.id]: e.target.value }))}
                  title="เลือก model ที่จะทดสอบ (auto = เลือกให้อัตโนมัติ)"
                >
                  <option value="">{cardLoading[p.id] ? "กำลังโหลด…" : "auto"}</option>
                  {(cardModels[p.id] ?? []).map(m => <option key={m.id} value={m.id}>{m.id}</option>)}
                </select>
              </div>
              {testResult[p.id] && <p className="text-xs text-slate-500 mt-1 break-all">{testResult[p.id]}</p>}
            </div>
          ))}
          {providers.length === 0 && !loading && (
            <p className="text-sm text-slate-400 col-span-2 text-center py-6">ยังไม่มี provider — กด "เพิ่ม Provider"</p>
          )}
        </div>
      </div>

      {/* Role assignments */}
      <div>
        <h2 className="text-sm font-bold text-slate-700 dark:text-slate-300 mb-2 flex items-center gap-1.5"><Zap size={14} /> Role Assignments (เรียง priority = ลำดับ failover)</h2>
        <div className="space-y-3">
          {roles.map(role => {
            const rows = assignments.filter(a => a.role === role).sort((x, y) => x.priority - y.priority);
            return (
              <div key={role} className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">{ROLE_LABELS[role] ?? role}</span>
                  <button onClick={() => { setCustomModel(false); setModelOpts([]); setAddRow({ role, provider_id: providers[0]?.id ?? "", model: "" }); }}
                    className="text-xs text-indigo-600 hover:underline flex items-center gap-1"><Plus size={11} /> เพิ่ม</button>
                </div>
                <div className="space-y-1.5">
                  {rows.map((a, i) => (
                    <div key={a.id} className="flex items-center gap-2 text-sm bg-slate-50 dark:bg-slate-800/50 rounded-lg px-2 py-1.5">
                      <span className="text-xs text-slate-400 w-5">{i + 1}.</span>
                      <span className="font-medium text-slate-700 dark:text-slate-200 w-24 truncate">{a.provider_name}</span>
                      <span className="font-mono text-xs text-slate-500 flex-1 truncate">{a.model}</span>
                      <span className={`w-2 h-2 rounded-full ${a.is_active ? "bg-emerald-500" : "bg-slate-400"}`} />
                      <button onClick={() => reorder(a, -1)} disabled={i === 0} className="p-1 text-slate-400 hover:text-slate-700 disabled:opacity-30"><ArrowUp size={12} /></button>
                      <button onClick={() => reorder(a, 1)} disabled={i === rows.length - 1} className="p-1 text-slate-400 hover:text-slate-700 disabled:opacity-30"><ArrowDown size={12} /></button>
                      <button onClick={() => updateAssignment(a, { is_active: !a.is_active })} className="p-1 text-slate-400 hover:text-slate-700"><Check size={12} /></button>
                      <button onClick={() => delAssignment(a.id)} className="p-1 text-red-400 hover:text-red-600"><Trash2 size={12} /></button>
                    </div>
                  ))}
                  {rows.length === 0 && <p className="text-xs text-slate-400">— ใช้ค่า .env (ไม่มี provider assign)</p>}

                  {addRow?.role === role && (
                    <div className="mt-1 space-y-1.5 rounded-lg bg-slate-50 dark:bg-slate-800/50 p-2">
                      <div className="flex items-center gap-2">
                        <select className={`${inputCls} w-32`} value={addRow.provider_id}
                          onChange={e => { setCustomModel(false); setAddRow({ ...addRow, provider_id: e.target.value, model: "" }); }}>
                          {providers.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                        </select>

                        {customModel ? (
                          <input className={`${inputCls} flex-1`} placeholder="พิมพ์ชื่อ model เอง"
                            value={addRow.model} onChange={e => setAddRow({ ...addRow, model: e.target.value })} />
                        ) : (
                          <select className={`${inputCls} flex-1`} value={addRow.model}
                            onChange={e => setAddRow({ ...addRow, model: e.target.value })} disabled={modelLoading}>
                            <option value="">{modelLoading ? "กำลังโหลด model…" : `— เลือก model (${modelOpts.length}) —`}</option>
                            {modelOpts.map(m => <option key={m.id} value={m.id}>{m.id}{m.free ? " · free" : ""}</option>)}
                          </select>
                        )}

                        <button onClick={() => addAssignment(role, addRow.provider_id, addRow.model, (rows.length + 1) * 10)}
                          disabled={!addRow.provider_id || !addRow.model}
                          className="px-2 py-1.5 rounded-lg bg-indigo-600 text-white text-xs disabled:opacity-40">เพิ่ม</button>
                        <button onClick={() => setAddRow(null)} className="p-1 text-slate-400"><X size={14} /></button>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-slate-500 pl-0.5">
                        <label className="flex items-center gap-1 cursor-pointer">
                          <input type="checkbox" checked={freeOnly} onChange={e => setFreeOnly(e.target.checked)} /> เฉพาะ free
                        </label>
                        <label className="flex items-center gap-1 cursor-pointer">
                          <input type="checkbox" checked={customModel} onChange={e => { setCustomModel(e.target.checked); setAddRow({ ...addRow, model: "" }); }} /> พิมพ์เอง
                        </label>
                        <button onClick={() => fetchModels(addRow.provider_id, freeOnly)}
                          className="flex items-center gap-1 text-indigo-600 hover:underline">
                          <RefreshCw size={11} className={modelLoading ? "animate-spin" : ""} /> โหลด model ใหม่
                        </button>
                        {modelErr && <span className="text-red-500 truncate">⚠ {modelErr}</span>}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {modal.open && <ProviderModal initial={modal.provider} onClose={() => setModal({ open: false, provider: null })} onSaved={() => { setModal({ open: false, provider: null }); load(); }} />}
    </div>
  );
}
