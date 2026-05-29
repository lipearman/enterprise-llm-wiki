"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { apiFetch, API_BASE } from "@/lib/api";

const DEFAULT_COMPANY = process.env.NEXT_PUBLIC_COMPANY_CODE || "DEVES";

// ── Relationship type → colour ─────────────────────────────────────────────

const REL_PALETTE: Record<string, string> = {
  has_coverage: "#3b82f6",
  requires:     "#f59e0b",
  part_of:      "#10b981",
  related_to:   "#8b5cf6",
  applies_to:   "#6366f1",
  excludes:     "#ef4444",
  contacts:     "#06b6d4",
  located_at:   "#84cc16",
  replaces:     "#f97316",
  depends_on:   "#ec4899",
};
const relColor = (t: string) => REL_PALETTE[t] ?? "#94a3b8";

// ── Types ──────────────────────────────────────────────────────────────────

interface SimNode {
  id: string;
  x: number; y: number;
  vx: number; vy: number;
  degree: number;
  pinned: boolean;
}
interface SimEdge {
  id: string;
  source: string; target: string;
  type: string;
  weight: number;
}

// ── Physics ────────────────────────────────────────────────────────────────

const REPULSION  = 9000;
const SPRING_K   = 0.035;
const SPRING_LEN = 170;
const GRAVITY    = 0.005;
const DAMPING    = 0.80;
const STABLE_THR = 0.08; // total KE below this → slow loop to 12 fps

const nodeR = (deg: number) => Math.max(10, Math.min(30, 8 + deg * 2.5));

// ──────────────────────────────────────────────────────────────────────────

export default function GraphPage() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wrapRef   = useRef<HTMLDivElement>(null);

  // Simulation state in refs (avoids React re-renders on every tick)
  const nodesRef      = useRef(new Map<string, SimNode>());
  const edgesRef      = useRef<SimEdge[]>([]);
  const rafId         = useRef(0);                          // requestAnimationFrame id
  const stableTimer   = useRef<ReturnType<typeof setTimeout> | null>(null); // idle throttle
  const stable        = useRef(false);

  // Viewport transform: canvas coords = world * scale + (tx, ty)
  const tfRef = useRef({ tx: 0, ty: 0, scale: 1 });

  // Interaction
  const dragRef    = useRef<{ id: string; ox: number; oy: number } | null>(null);
  const panRef     = useRef<{ sx: number; sy: number; tx: number; ty: number } | null>(null);
  const hoverRef   = useRef<string | null>(null);
  const selRef     = useRef<string | null>(null);

  // React UI state
  const [company,      setCompany]      = useState(DEFAULT_COMPANY);
  const [relTypes,     setRelTypes]     = useState<string[]>([]);
  const [filterType,   setFilterType]   = useState("");
  const [search,       setSearch]       = useState("");
  const [loading,      setLoading]      = useState(false);
  const [stats,        setStats]        = useState({ nodes: 0, edges: 0 });
  const [selectedInfo, setSelectedInfo] = useState<{ id: string; rels: SimEdge[] } | null>(null);

  // ── Build simulation graph from API response ─────────────────────────────

  const buildGraph = useCallback((items: any[]) => {
    const nm = new Map<string, SimNode>();
    const el: SimEdge[] = [];

    for (const rel of items) {
      for (const id of [rel.source_entity, rel.target_entity]) {
        if (!nm.has(id)) {
          nm.set(id, {
            id,
            x: (Math.random() - 0.5) * 900,
            y: (Math.random() - 0.5) * 900,
            vx: 0, vy: 0, degree: 0, pinned: false,
          });
        }
      }
      nm.get(rel.source_entity)!.degree++;
      nm.get(rel.target_entity)!.degree++;
      el.push({
        id:     rel.id,
        source: rel.source_entity,
        target: rel.target_entity,
        type:   rel.relationship_type,
        weight: rel.weight ?? 1,
      });
    }

    nodesRef.current = nm;
    edgesRef.current = el;
    stable.current   = false;

    const types = [...new Set(el.map(e => e.type))].sort();
    setRelTypes(types);
    setStats({ nodes: nm.size, edges: el.length });

    const cv = canvasRef.current;
    if (cv) tfRef.current = { tx: cv.width / 2, ty: cv.height / 2, scale: 1 };
  }, []);

  // ── Load from API ─────────────────────────────────────────────────────────

  const loadGraph = useCallback(async () => {
    setLoading(true);
    setSelectedInfo(null);
    selRef.current = null;
    try {
      const p = new URLSearchParams({ company_code: company, limit: "500" });
      const res  = await apiFetch(`${API_BASE}/api/wiki/relationships?${p}`);
      const data = await res.json();
      buildGraph(data.items ?? []);
    } finally {
      setLoading(false);
    }
  }, [company, buildGraph]);

  useEffect(() => { loadGraph(); }, [loadGraph]);

  // ── Canvas render ─────────────────────────────────────────────────────────

  const draw = useCallback(() => {
    const cv = canvasRef.current;
    if (!cv) return;
    const ctx  = cv.getContext("2d")!;
    const { tx, ty, scale } = tfRef.current;
    const searchLo = search.toLowerCase();

    ctx.clearRect(0, 0, cv.width, cv.height);
    ctx.save();
    ctx.translate(tx, ty);
    ctx.scale(scale, scale);

    const visEdges = filterType
      ? edgesRef.current.filter(e => e.type === filterType)
      : edgesRef.current;

    // ── Edges ──────────────────────────────────────────────────────────────
    for (const e of visEdges) {
      const s = nodesRef.current.get(e.source);
      const t = nodesRef.current.get(e.target);
      if (!s || !t) continue;

      const hi = selRef.current &&
        (e.source === selRef.current || e.target === selRef.current);

      const color = relColor(e.type);
      ctx.globalAlpha = hi ? 0.9 : 0.3;
      ctx.strokeStyle  = color;
      ctx.lineWidth    = hi ? 2.5 : 1.2;
      ctx.beginPath();
      ctx.moveTo(s.x, s.y);
      ctx.lineTo(t.x, t.y);
      ctx.stroke();

      // Arrow head at target
      const ang = Math.atan2(t.y - s.y, t.x - s.x);
      const r   = nodeR(t.degree);
      const ax  = t.x - Math.cos(ang) * r;
      const ay  = t.y - Math.sin(ang) * r;
      ctx.beginPath();
      ctx.moveTo(ax, ay);
      ctx.lineTo(ax - 9 * Math.cos(ang - 0.45), ay - 9 * Math.sin(ang - 0.45));
      ctx.lineTo(ax - 9 * Math.cos(ang + 0.45), ay - 9 * Math.sin(ang + 0.45));
      ctx.closePath();
      ctx.fillStyle = color;
      ctx.fill();

      // Edge label (only when zoomed in enough or highlighted)
      if (hi || scale > 1.2) {
        ctx.globalAlpha = 0.7;
        ctx.fillStyle   = color;
        ctx.font        = "9px sans-serif";
        ctx.textAlign   = "center";
        ctx.fillText(e.type, (s.x + t.x) / 2, (s.y + t.y) / 2 - 4);
      }
    }

    ctx.globalAlpha = 1;

    // ── Nodes ──────────────────────────────────────────────────────────────
    for (const [id, n] of nodesRef.current) {
      const r       = nodeR(n.degree);
      const isSel   = selRef.current === id;
      const isHov   = hoverRef.current === id;
      const isMatch = searchLo && id.toLowerCase().includes(searchLo);

      // Glow for selected / search match
      if (isSel || isMatch) {
        ctx.beginPath();
        ctx.arc(n.x, n.y, r + 6, 0, Math.PI * 2);
        ctx.fillStyle = isSel ? "rgba(59,130,246,0.25)" : "rgba(217,119,6,0.25)";
        ctx.fill();
      }

      // Node fill
      ctx.beginPath();
      ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
      ctx.fillStyle = isSel   ? "#2563eb"
                    : isMatch ? "#d97706"
                    : isHov   ? "#475569"
                    :           "#334155";
      ctx.fill();
      ctx.strokeStyle = "#e2e8f0";
      ctx.lineWidth   = isSel ? 2.5 : 1.5;
      ctx.stroke();

      // Degree badge (for high-degree nodes)
      if (n.degree >= 4) {
        ctx.fillStyle = "#f1f5f9";
        ctx.font      = "bold 9px sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(String(n.degree), n.x, n.y + 3.5);
      }

      // Label below node
      const label = id.length > 22 ? id.slice(0, 20) + "…" : id;
      ctx.fillStyle = isSel   ? "#93c5fd"
                    : isMatch ? "#fcd34d"
                    : isHov   ? "#e2e8f0"
                    :           "#94a3b8";
      ctx.font      = `${isSel || isHov ? "bold " : ""}10.5px sans-serif`;
      ctx.textAlign = "center";
      ctx.fillText(label, n.x, n.y + r + 14);
    }

    ctx.restore();
  }, [search, filterType]);

  // ── Force simulation tick ─────────────────────────────────────────────────

  const tick = useCallback(() => {
    const narr = Array.from(nodesRef.current.values());
    let ke = 0;

    // Gravity + Repulsion
    for (const n of narr) {
      if (n.pinned) continue;
      n.vx += -n.x * GRAVITY;
      n.vy += -n.y * GRAVITY;

      for (const m of narr) {
        if (m === n) continue;
        const dx = n.x - m.x, dy = n.y - m.y;
        const d2 = dx * dx + dy * dy || 0.01;
        const d  = Math.sqrt(d2);
        const f  = REPULSION / d2;
        n.vx += (dx / d) * f;
        n.vy += (dy / d) * f;
      }
    }

    // Spring (edges)
    for (const e of edgesRef.current) {
      const s = nodesRef.current.get(e.source);
      const t = nodesRef.current.get(e.target);
      if (!s || !t) continue;
      const dx = t.x - s.x, dy = t.y - s.y;
      const d  = Math.sqrt(dx * dx + dy * dy) || 1;
      const f  = (d - SPRING_LEN) * SPRING_K * e.weight;
      if (!s.pinned) { s.vx += (dx / d) * f; s.vy += (dy / d) * f; }
      if (!t.pinned) { t.vx -= (dx / d) * f; t.vy -= (dy / d) * f; }
    }

    // Integrate + damping
    for (const n of narr) {
      if (n.pinned) continue;
      n.vx *= DAMPING; n.vy *= DAMPING;
      n.x  += n.vx;    n.y  += n.vy;
      ke   += n.vx * n.vx + n.vy * n.vy;
    }

    draw();

    // Throttle to ~12 fps when graph is stable (saves CPU)
    stable.current = ke < STABLE_THR;
    if (stable.current && !dragRef.current) {
      stableTimer.current = setTimeout(() => {
        stableTimer.current = null;
        rafId.current = requestAnimationFrame(tick);
      }, 80);
    } else {
      rafId.current = requestAnimationFrame(tick);
    }
  }, [draw]);

  // Start / restart animation loop when graph data changes
  useEffect(() => {
    cancelAnimationFrame(rafId.current);
    if (stableTimer.current) { clearTimeout(stableTimer.current); stableTimer.current = null; }
    rafId.current = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(rafId.current);
      if (stableTimer.current) clearTimeout(stableTimer.current);
    };
  }, [tick]);

  // Wheel zoom — must be a non-passive native listener so preventDefault() works
  useEffect(() => {
    const cv = canvasRef.current;
    if (!cv) return;
    const handler = (e: WheelEvent) => {
      e.preventDefault();
      const rect   = cv.getBoundingClientRect();
      const cx     = e.clientX - rect.left;
      const cy     = e.clientY - rect.top;
      const factor = e.deltaY < 0 ? 1.12 : 0.89;
      const { tx, ty, scale } = tfRef.current;
      tfRef.current = {
        scale: Math.max(0.08, Math.min(6, scale * factor)),
        tx:    cx - (cx - tx) * factor,
        ty:    cy - (cy - ty) * factor,
      };
      stable.current = false;
    };
    cv.addEventListener("wheel", handler, { passive: false });
    return () => cv.removeEventListener("wheel", handler);
  }, []);

  // ── Resize observer (keeps canvas pixel-perfect) ──────────────────────────

  useEffect(() => {
    const wrap = wrapRef.current;
    const cv   = canvasRef.current;
    if (!wrap || !cv) return;
    const ro = new ResizeObserver(() => {
      cv.width  = wrap.clientWidth;
      cv.height = wrap.clientHeight;
    });
    ro.observe(wrap);
    return () => ro.disconnect();
  }, []);

  // ── Coordinate helpers ────────────────────────────────────────────────────

  function toWorld(cx: number, cy: number) {
    const { tx, ty, scale } = tfRef.current;
    return { x: (cx - tx) / scale, y: (cy - ty) / scale };
  }

  function hitNode(wx: number, wy: number): string | null {
    for (const [id, n] of nodesRef.current) {
      const r = nodeR(n.degree);
      if ((n.x - wx) ** 2 + (n.y - wy) ** 2 <= r * r) return id;
    }
    return null;
  }

  function canvasXY(e: React.MouseEvent) {
    const rect = canvasRef.current!.getBoundingClientRect();
    return { cx: e.clientX - rect.left, cy: e.clientY - rect.top };
  }

  // ── Mouse handlers ────────────────────────────────────────────────────────

  function onMouseDown(e: React.MouseEvent) {
    const { cx, cy } = canvasXY(e);
    const { x, y }   = toWorld(cx, cy);
    const hit = hitNode(x, y);

    if (hit) {
      const n = nodesRef.current.get(hit)!;
      n.pinned  = true;
      dragRef.current = { id: hit, ox: x - n.x, oy: y - n.y };
    } else {
      panRef.current = { sx: cx, sy: cy, tx: tfRef.current.tx, ty: tfRef.current.ty };
    }
    stable.current = false; // wake up loop
  }

  function onMouseMove(e: React.MouseEvent) {
    const { cx, cy } = canvasXY(e);

    if (dragRef.current) {
      const { x, y } = toWorld(cx, cy);
      const n = nodesRef.current.get(dragRef.current.id)!;
      n.x = x - dragRef.current.ox;
      n.y = y - dragRef.current.oy;
      n.vx = n.vy = 0;
      return;
    }
    if (panRef.current) {
      tfRef.current.tx = panRef.current.tx + (cx - panRef.current.sx);
      tfRef.current.ty = panRef.current.ty + (cy - panRef.current.sy);
      return;
    }

    const { x, y } = toWorld(cx, cy);
    const hit = hitNode(x, y);
    hoverRef.current = hit;
    canvasRef.current!.style.cursor = hit ? "pointer" : "grab";
  }

  function onMouseUp(e: React.MouseEvent) {
    if (dragRef.current) {
      const { cx, cy } = canvasXY(e);
      const { x, y }   = toWorld(cx, cy);
      const id = dragRef.current.id;
      const n  = nodesRef.current.get(id)!;

      // Click (not drag): toggle selection
      const moved = Math.hypot(x - n.x - dragRef.current.ox, y - n.y - dragRef.current.oy);
      if (moved < 5) {
        if (selRef.current === id) {
          selRef.current = null;
          setSelectedInfo(null);
        } else {
          selRef.current = id;
          const rels = edgesRef.current.filter(ed => ed.source === id || ed.target === id);
          setSelectedInfo({ id, rels });
        }
      }

      n.pinned = false;
      dragRef.current = null;
    }
    panRef.current = null;
  }

  // ── Toolbar actions ───────────────────────────────────────────────────────

  function zoomFit() {
    const cv = canvasRef.current;
    if (!cv || !nodesRef.current.size) return;
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (const n of nodesRef.current.values()) {
      minX = Math.min(minX, n.x); maxX = Math.max(maxX, n.x);
      minY = Math.min(minY, n.y); maxY = Math.max(maxY, n.y);
    }
    const pad = 80;
    const s   = Math.min(
      (cv.width  - pad * 2) / (maxX - minX || 1),
      (cv.height - pad * 2) / (maxY - minY || 1),
      2,
    );
    tfRef.current = {
      scale: s,
      tx: cv.width  / 2 - ((minX + maxX) / 2) * s,
      ty: cv.height / 2 - ((minY + maxY) / 2) * s,
    };
    stable.current = false;
  }

  function resetLayout() {
    for (const n of nodesRef.current.values()) {
      n.x = (Math.random() - 0.5) * 900;
      n.y = (Math.random() - 0.5) * 900;
      n.vx = n.vy = 0;
    }
    const cv = canvasRef.current;
    if (cv) tfRef.current = { tx: cv.width / 2, ty: cv.height / 2, scale: 1 };
    stable.current = false;
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col gap-4">

      {/* ── Header bar ─────────────────────────────────────────────────────── */}
      <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 p-5 shadow-sm flex flex-wrap items-center gap-3">
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-slate-800 dark:text-white">🕸️ Knowledge Graph</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            {loading ? "กำลังโหลด…" : `${stats.nodes} entities · ${stats.edges} relationships`}
            {" · "}คลิก node เพื่อดูรายละเอียด · scroll เพื่อ zoom
          </p>
        </div>

        {/* Controls */}
        <select value={company} onChange={e => setCompany(e.target.value)}
          className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
          <option value="DEVES">DEVES</option>
          <option value="LOCKTON">LOCKTON</option>
        </select>

        <select value={filterType} onChange={e => setFilterType(e.target.value)}
          className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
          <option value="">ทุก relationship type</option>
          {relTypes.map(t => <option key={t} value={t}>{t}</option>)}
        </select>

        <input
          value={search} onChange={e => setSearch(e.target.value)}
          placeholder="🔍 ค้นหา entity…"
          className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-500 px-3 py-1.5 text-sm w-44 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        <button onClick={zoomFit}
          className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 font-mono transition-colors">
          ⊞ Fit
        </button>
        <button onClick={resetLayout}
          className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors">
          🔄 Reset
        </button>
      </div>

      {/* ── Main canvas + side panel ────────────────────────────────────────── */}
      <div className="flex gap-4" style={{ height: "calc(100vh - 230px)" }}>

        {/* Canvas area */}
        <div ref={wrapRef}
          className="relative flex-1 rounded-2xl bg-slate-900 shadow-sm overflow-hidden">

          {/* Empty state */}
          {!loading && stats.nodes === 0 && (
            <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-500 text-sm z-10 pointer-events-none">
              <div className="text-5xl mb-3">🕸️</div>
              <p className="font-medium">ยังไม่มี entity relationships</p>
              <p className="text-xs mt-1 text-slate-600">
                Ingest URL พร้อม Deep Enrichment เพื่อสร้าง knowledge graph อัตโนมัติ
              </p>
            </div>
          )}

          <canvas
            ref={canvasRef}
            className="w-full h-full"
            onMouseDown={onMouseDown}
            onMouseMove={onMouseMove}
            onMouseUp={onMouseUp}
            onMouseLeave={() => { hoverRef.current = null; panRef.current = null; }}
          />

          {/* Relationship-type legend (bottom-left) */}
          {relTypes.length > 0 && (
            <div className="absolute bottom-3 left-3 bg-slate-800/90 backdrop-blur rounded-xl p-3 space-y-1 max-h-52 overflow-y-auto">
              <p className="text-xs text-slate-400 font-semibold uppercase tracking-wide mb-1.5">
                Relationship types
              </p>
              {relTypes.map(t => (
                <button key={t}
                  onClick={() => setFilterType(filterType === t ? "" : t)}
                  className="flex items-center gap-2 w-full text-left"
                >
                  <span className="w-2.5 h-2.5 rounded-full shrink-0"
                    style={{ background: relColor(t) }} />
                  <span className={`text-xs ${filterType === t
                    ? "text-white font-bold"
                    : "text-slate-300 hover:text-white"}`}>
                    {t}
                  </span>
                </button>
              ))}
              {filterType && (
                <button onClick={() => setFilterType("")}
                  className="text-xs text-slate-500 hover:text-slate-300 mt-1">
                  ✕ แสดงทั้งหมด
                </button>
              )}
            </div>
          )}

          {/* Controls hint (top-right) */}
          <div className="absolute top-3 right-3 text-xs text-slate-500
            bg-slate-800/70 backdrop-blur rounded-lg px-2.5 py-1.5 leading-relaxed pointer-events-none">
            🖱 scroll: zoom · drag: pan · click node: details
          </div>

          {/* Search match count */}
          {search && (
            <div className="absolute top-3 left-3 text-xs bg-amber-500/90 text-white
              rounded-lg px-2.5 py-1.5 font-medium pointer-events-none">
              🔍 {[...nodesRef.current.keys()].filter(id =>
                id.toLowerCase().includes(search.toLowerCase())).length} ตรงกัน
            </div>
          )}
        </div>

        {/* ── Side panel: selected node ─────────────────────────────────────── */}
        {selectedInfo && (
          <div className="w-72 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm flex flex-col overflow-hidden">
            {/* Header */}
            <div className="p-4 border-b border-slate-200 dark:border-slate-800 bg-indigo-50 dark:bg-indigo-950/30">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-xs text-indigo-500 dark:text-indigo-400 font-semibold uppercase tracking-wide mb-0.5">
                    Entity
                  </p>
                  <h3 className="font-bold text-slate-800 dark:text-white text-sm leading-tight break-words">
                    {selectedInfo.id}
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                    {selectedInfo.rels.length} relationships ·{" "}
                    degree {nodesRef.current.get(selectedInfo.id)?.degree ?? 0}
                  </p>
                </div>
                <button
                  onClick={() => { selRef.current = null; setSelectedInfo(null); }}
                  className="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 text-lg leading-none shrink-0 mt-0.5 transition-colors"
                >✕</button>
              </div>
            </div>

            {/* Relationship list */}
            <div className="flex-1 overflow-y-auto p-3 space-y-1.5">
              {selectedInfo.rels.length === 0 && (
                <p className="text-xs text-slate-400 dark:text-slate-600 text-center py-6">ไม่มี relationship</p>
              )}
              {selectedInfo.rels.map(e => {
                const isSource = e.source === selectedInfo.id;
                const other    = isSource ? e.target : e.source;
                return (
                  <button key={e.id}
                    className="w-full text-left rounded-xl border border-slate-200 dark:border-slate-700 px-3 py-2
                               hover:bg-slate-50 dark:hover:bg-slate-800/60 transition-colors group"
                    onClick={() => {
                      selRef.current = other;
                      const rels = edgesRef.current.filter(
                        ed => ed.source === other || ed.target === other,
                      );
                      setSelectedInfo({ id: other, rels });
                    }}
                  >
                    <div className="flex items-center gap-1.5 mb-1">
                      <span className="w-2 h-2 rounded-full shrink-0"
                        style={{ background: relColor(e.type) }} />
                      <span className="text-xs font-semibold"
                        style={{ color: relColor(e.type) }}>
                        {e.type}
                      </span>
                      <span className="ml-auto text-slate-400 dark:text-slate-500 text-xs font-mono">
                        {isSource ? "→" : "←"}
                      </span>
                    </div>
                    <p className="text-xs text-slate-700 dark:text-slate-300 font-medium truncate
                      group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                      {other}
                    </p>
                    {e.weight !== 1 && (
                      <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
                        weight: {e.weight}
                      </p>
                    )}
                  </button>
                );
              })}
            </div>

            {/* Stats footer */}
            <div className="border-t border-slate-200 dark:border-slate-800 px-4 py-3 bg-slate-50 dark:bg-slate-800/50 text-xs text-slate-500 dark:text-slate-400 flex gap-4">
              <span>ออก: {selectedInfo.rels.filter(e => e.source === selectedInfo.id).length}</span>
              <span>เข้า: {selectedInfo.rels.filter(e => e.target === selectedInfo.id).length}</span>
              <span className="ml-auto text-slate-400 dark:text-slate-500">คลิก entity อื่นเพื่อ navigate</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
