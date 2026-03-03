// src/atlas/frontend/src/App.jsx
import React, { useEffect, useMemo, useRef, useState } from "react";
import Charts from "./Charts";

// ============================================================
// Constantes UI (fallback si el backend no manda symbols)
// ============================================================
// MT5 con sufijo z (regla proyecto)
const DEFAULT_SYMBOLS = [
  "XAUUSDz",
  "EURUSDz",
  "GBPUSDz",
  "USDJPYz",
  "USDCHFz",
  "USDCADz",
  "AUDUSDz",
  "NZDUSDz",
  "EURJPYz",
  "GBPJPYz",
];

const WORLDS = ["ATLAS_IA", "GAP", "PRESESION", "GATILLO", "BITACORA"];
const ATLAS_MODES = ["SCALPING_M1", "SCALPING_M5", "FOREX"];

function clampStr(x) {
  if (x == null) return "";
  return String(x);
}

function safeNum(x, d = 0) {
  const n = Number(x);
  return Number.isFinite(n) ? n : d;
}

function normalizeSnapshot(raw) {
  // Backend: SnapshotResponse { ok, world, atlas_mode, payload }
  // Queremos trabajar con payload como "snapshot" final.
  if (!raw) return null;

  const payload = raw.payload && typeof raw.payload === "object" ? raw.payload : raw;

  // Algunos mundos pueden devolver distinto, por eso armamos un contrato mínimo.
  const snapshot = {
    ok: raw.ok ?? payload.ok ?? true,
    world: clampStr(payload.world || raw.world || ""),
    atlas_mode: clampStr(payload.atlas_mode || raw.atlas_mode || raw.atlas_mode || ""),
    symbol: clampStr(payload.symbol || ""),
    tf: clampStr(payload.tf || ""),
    ts_ms: safeNum(payload.ts_ms || raw.ts_ms, Date.now()),
    candles: Array.isArray(payload.candles) ? payload.candles : [],
    meta: payload.meta && typeof payload.meta === "object" ? payload.meta : {},
    state: clampStr(payload.state || (payload.analysis && payload.analysis.state) || ""),
    side: clampStr(payload.side || (payload.analysis && payload.analysis.side) || ""),
    price: safeNum(payload.price, 0),
    zone: payload.zone ?? [0, 0],
    note: clampStr(payload.note || (payload.analysis && payload.analysis.note) || ""),
    score: safeNum(payload.score, 0),
    light: clampStr(payload.light || ""),
    analysis: payload.analysis && typeof payload.analysis === "object" ? payload.analysis : {},
    ui: payload.ui && typeof payload.ui === "object" ? payload.ui : { rows: [] },
    // Root trade fields (si SIGNAL)
    entry: safeNum(payload.entry, 0),
    sl: safeNum(payload.sl, 0),
    tp: safeNum(payload.tp, 0),
    trade: payload.trade ?? null,
    last_error: payload.last_error ?? null,
    bitacora: payload.bitacora ?? null,
    events: payload.events ?? null,
  };

  return snapshot;
}

function lightEmoji(light) {
  const L = (light || "").toUpperCase();
  if (L === "GREEN") return "🟢";
  if (L === "YELLOW") return "🟡";
  if (L === "RED") return "🔴";
  return "⚪";
}

function isSuccessLastError(last_error) {
  // Regla proyecto: [1,"Success"] NO es error real
  if (!last_error) return true;
  try {
    if (Array.isArray(last_error) && last_error.length >= 2) {
      const code = Number(last_error[0]);
      const msg = String(last_error[1] || "");
      if (code === 1 && msg.toLowerCase().includes("success")) return true;
    }
  } catch {}
  return false;
}

export default function App() {
  // ---------------------------
  // Estado UI
  // ---------------------------
  const [world, setWorld] = useState("ATLAS_IA");
  const [atlasMode, setAtlasMode] = useState("SCALPING_M1");
  const [symbol, setSymbol] = useState("XAUUSDz");
  const [tf, setTf] = useState("M1"); // informativo para header (backend manda real)
  const [symbols, setSymbols] = useState(DEFAULT_SYMBOLS);

  const [snapshot, setSnapshot] = useState(null);
  const [loading, setLoading] = useState(true);
  const [pollMs, setPollMs] = useState(900);

  // Feed status solo UI (optimista)
  const [feedStatus, setFeedStatus] = useState("UNKNOWN"); // RUNNING | PAUSED | RESET | UNKNOWN
  const [lastAction, setLastAction] = useState("");

  const abortRef = useRef(null);

  // ---------------------------
  // Query snapshot
  // ---------------------------
  const snapshotUrl = useMemo(() => {
    const params = new URLSearchParams();
    params.set("world", world);

    if (world === "ATLAS_IA") {
      params.set("atlas_mode", atlasMode);
    }

    // Si tu backend snapshot soporta symbol/tf: se lo pasamos.
    // Si no lo soporta, no rompe: el backend ignora query extra.
    params.set("symbol", symbol);

    return `/api/snapshot?${params.toString()}`;
  }, [world, atlasMode, symbol]);

  // ---------------------------
  // Polling ÚNICO a /api/snapshot (mandamiento)
  // ---------------------------
  useEffect(() => {
    let mounted = true;

    async function tick() {
      if (!mounted) return;

      try {
        setLoading(true);

        // cancelar request anterior si se superpone
        if (abortRef.current) abortRef.current.abort();
        const controller = new AbortController();
        abortRef.current = controller;

        const res = await fetch(snapshotUrl, { signal: controller.signal });
        const json = await res.json();

        const snap = normalizeSnapshot(json);
        if (!snap) return;

        // Ajustar símbolos si backend manda lista (opcional)
        // Si el backend te devuelve meta.symbols o ui.meta.symbols, lo tomamos.
        const backendSymbols =
          (snap.meta && Array.isArray(snap.meta.symbols) && snap.meta.symbols) ||
          (snap.ui && snap.ui.meta && Array.isArray(snap.ui.meta.symbols) && snap.ui.meta.symbols) ||
          null;

        if (backendSymbols && backendSymbols.length > 0) {
          setSymbols(backendSymbols);
        }

        // tf real si viene
        if (snap.tf) setTf(snap.tf);

        if (mounted) setSnapshot(snap);
      } catch (e) {
        // silencio: no queremos romper UI
      } finally {
        if (mounted) setLoading(false);
      }
    }

    // primera
    tick();

    // intervalo
    const id = setInterval(tick, pollMs);

    return () => {
      mounted = false;
      clearInterval(id);
      try {
        if (abortRef.current) abortRef.current.abort();
      } catch {}
    };
  }, [snapshotUrl, pollMs]);

  // ---------------------------
  // Acciones Feed (POST) - fuera del polling (ok)
  // ---------------------------
  async function postFeed(path, optimisticStatus) {
    try {
      setLastAction(path);
      const res = await fetch(path, { method: "POST" });
      const j = await res.json().catch(() => ({}));
      setFeedStatus(j.status || optimisticStatus || "UNKNOWN");
    } catch {
      setFeedStatus("UNKNOWN");
    } finally {
      setTimeout(() => setLastAction(""), 700);
    }
  }

  // ---------------------------
  // Checklist: datos UI
  // ---------------------------
  const checklist = useMemo(() => {
    const s = snapshot || {};
    const a = s.analysis || {};
    const planFrozen =
      typeof a.plan_frozen === "boolean"
        ? a.plan_frozen
        : typeof a.plan_frozen === "undefined"
        ? Boolean(s.plan)
        : Boolean(a.plan_frozen);

    const signalFrozen =
      typeof a.signal_frozen === "boolean"
        ? a.signal_frozen
        : typeof a.signal_frozen === "undefined"
        ? Boolean(s.signal)
        : Boolean(a.signal_frozen);

    return {
      world: s.world || world,
      atlas_mode: world === "ATLAS_IA" ? atlasMode : "",
      symbol: s.symbol || symbol,
      tf: s.tf || tf,
      state: s.state || "WAIT",
      side: s.side || "WAIT",
      price: safeNum(s.price, 0),
      note: s.note || (a.reason ? String(a.reason) : ""),
      score: safeNum(s.score, 0),
      light: s.light || "GRAY",
      planFrozen,
      signalFrozen,
      entry: safeNum(s.entry, 0),
      sl: safeNum(s.sl, 0),
      tp: safeNum(s.tp, 0),
      lastErrorOk: isSuccessLastError(s.last_error),
      last_error: s.last_error,
    };
  }, [snapshot, world, atlasMode, symbol, tf]);

  // ---------------------------
  // Render
  // ---------------------------
  return (
    <div style={{ fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, Arial" }}>
      <div style={{ padding: 14, display: "flex", gap: 14, alignItems: "center", flexWrap: "wrap" }}>
        <h2 style={{ margin: 0 }}>TEAM ATLAS</h2>

        {/* Mundo */}
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <span style={{ opacity: 0.8 }}>Mundo</span>
          <select
            value={world}
            onChange={(e) => setWorld(e.target.value)}
            style={{ padding: "6px 8px" }}
          >
            {WORLDS.map((w) => (
              <option key={w} value={w}>
                {w}
              </option>
            ))}
          </select>
        </div>

        {/* Submodo ATLAS_IA */}
        {world === "ATLAS_IA" && (
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <span style={{ opacity: 0.8 }}>Isla</span>
            <select
              value={atlasMode}
              onChange={(e) => setAtlasMode(e.target.value)}
              style={{ padding: "6px 8px" }}
            >
              {ATLAS_MODES.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Polling */}
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <span style={{ opacity: 0.8 }}>Poll</span>
          <select
            value={pollMs}
            onChange={(e) => setPollMs(Number(e.target.value))}
            style={{ padding: "6px 8px" }}
          >
            <option value={600}>600ms</option>
            <option value={900}>900ms</option>
            <option value={1200}>1200ms</option>
            <option value={1800}>1800ms</option>
          </select>
        </div>

        {/* Feed controls */}
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <button
            onClick={() => postFeed("/api/feed/play", "RUNNING")}
            style={{ padding: "6px 10px", cursor: "pointer" }}
          >
            ▶️ Play
          </button>
          <button
            onClick={() => postFeed("/api/feed/pause", "PAUSED")}
            style={{ padding: "6px 10px", cursor: "pointer" }}
          >
            ⏸ Pause
          </button>
          <button
            onClick={() => postFeed("/api/feed/reset", "RESET")}
            style={{ padding: "6px 10px", cursor: "pointer" }}
          >
            ♻️ Reset
          </button>

          <span style={{ fontSize: 13, opacity: 0.85 }}>
            Feed: <b>{feedStatus}</b> {lastAction ? `(${lastAction})` : ""}
          </span>
        </div>

        {/* Status */}
        <div style={{ marginLeft: "auto", fontSize: 13, opacity: 0.85 }}>
          {loading ? "cargando..." : "ok"} • endpoint:{" "}
          <code style={{ fontSize: 12 }}>{snapshotUrl}</code>
        </div>
      </div>

      {/* Layout principal */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 360px", gap: 14, padding: 14 }}>
        {/* Col izquierda: Chart + símbolos */}
        <div style={{ minWidth: 0 }}>
          <div
            style={{
              border: "1px solid rgba(0,0,0,0.12)",
              borderRadius: 12,
              padding: 12,
              marginBottom: 10,
            }}
          >
            <div style={{ display: "flex", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
              <div style={{ fontSize: 14, opacity: 0.85 }}>
                {checklist.world}
                {world === "ATLAS_IA" ? ` / ${atlasMode}` : ""}
              </div>
              <div style={{ fontSize: 18, fontWeight: 700 }}>{checklist.symbol}</div>
              <div style={{ fontSize: 13, opacity: 0.7 }}>{checklist.tf}</div>
              <div style={{ marginLeft: "auto", fontSize: 14 }}>
                {lightEmoji(checklist.light)} <b>{checklist.state}</b> • {checklist.side}
              </div>
            </div>

            <div style={{ marginTop: 10 }}>
              <Charts snapshot={snapshot} />
            </div>

            {/* Símbolos clickeables */}
            <div style={{ marginTop: 10, display: "flex", flexWrap: "wrap", gap: 8 }}>
              {symbols.map((s) => {
                const active = s === symbol;
                return (
                  <button
                    key={s}
                    onClick={() => setSymbol(s)}
                    style={{
                      cursor: "pointer",
                      padding: "6px 8px",
                      borderRadius: 10,
                      border: "1px solid rgba(0,0,0,0.14)",
                      background: active ? "rgba(0,0,0,0.06)" : "transparent",
                      fontSize: 12, // 25% más chico aprox
                      fontWeight: active ? 700 : 500,
                    }}
                    title="Click para cambiar símbolo"
                  >
                    {s}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Panel de filas UI (si el backend las manda) */}
          <div style={{ border: "1px solid rgba(0,0,0,0.12)", borderRadius: 12, padding: 12 }}>
            <div style={{ fontWeight: 700, marginBottom: 8 }}>UI Rows</div>
            <div style={{ display: "grid", gap: 6 }}>
              {(snapshot?.ui?.rows || []).map((r, idx) => {
                const k = r.k ?? r.key ?? r.trade_id ?? `row_${idx}`;
                const v = r.v ?? r.value ?? r.event ?? "";
                return (
                  <div
                    key={`${k}_${idx}`}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      gap: 10,
                      padding: "6px 8px",
                      borderRadius: 10,
                      background: "rgba(0,0,0,0.03)",
                      fontSize: 13,
                    }}
                  >
                    <div style={{ opacity: 0.8 }}>{k}</div>
                    <div style={{ fontWeight: 600, textAlign: "right" }}>{String(v)}</div>
                  </div>
                );
              })}
              {(!snapshot?.ui?.rows || snapshot.ui.rows.length === 0) && (
                <div style={{ opacity: 0.7, fontSize: 13 }}>sin rows</div>
              )}
            </div>
          </div>
        </div>

        {/* Col derecha: Checklist */}
        <div style={{ border: "1px solid rgba(0,0,0,0.12)", borderRadius: 12, padding: 12 }}>
          <div style={{ fontWeight: 800, fontSize: 16, marginBottom: 10 }}>Checklist</div>

          <div style={{ display: "grid", gap: 8 }}>
            <Row label="Mundo" value={checklist.world} />
            {world === "ATLAS_IA" && <Row label="Isla" value={atlasMode} />}
            <Row label="Símbolo" value={checklist.symbol} />
            <Row label="TF" value={checklist.tf} />
            <Row label="Estado" value={`${lightEmoji(checklist.light)} ${checklist.state}`} />
            <Row label="Lado" value={checklist.side} />
            <Row label="Precio" value={checklist.price ? checklist.price : "-"} />
            <Row label="Score" value={checklist.score} />
            <Row label="Plan congelado" value={checklist.planFrozen ? "Sí" : "No"} />
            <Row label="Señal congelada" value={checklist.signalFrozen ? "Sí" : "No"} />

            <div style={{ marginTop: 6, padding: 10, borderRadius: 12, background: "rgba(0,0,0,0.03)" }}>
              <div style={{ fontSize: 12, opacity: 0.75, marginBottom: 6 }}>Nota</div>
              <div style={{ fontSize: 13, fontWeight: 600 }}>{checklist.note || "—"}</div>
            </div>

            {/* Trade fields (si hay SIGNAL) */}
            <div style={{ marginTop: 6 }}>
              <div style={{ fontWeight: 800, marginBottom: 6 }}>Plan (ROOT)</div>
              <Row label="Entry" value={checklist.entry > 0 ? checklist.entry : "—"} />
              <Row label="SL" value={checklist.sl > 0 ? checklist.sl : "—"} />
              <Row label="TP" value={checklist.tp > 0 ? checklist.tp : "—"} />
            </div>

            {/* last_error */}
            {!checklist.lastErrorOk && (
              <div
                style={{
                  marginTop: 8,
                  padding: 10,
                  borderRadius: 12,
                  background: "rgba(255,0,0,0.08)",
                  fontSize: 13,
                }}
              >
                <b>last_error</b>: {JSON.stringify(checklist.last_error)}
              </div>
            )}

            {/* Bitácora quick view si viene en snapshot */}
            {snapshot?.world === "BITACORA" && (
              <div style={{ marginTop: 10 }}>
                <div style={{ fontWeight: 800, marginBottom: 6 }}>Bitácora</div>
                <Row label="Eventos" value={safeNum(snapshot?.analysis?.events_count, 0)} />
                <Row label="Cerrados" value={safeNum(snapshot?.analysis?.stats?.total_trades_closed, 0)} />
                <Row label="TP" value={safeNum(snapshot?.analysis?.stats?.tp_final_count, 0)} />
                <Row label="SL" value={safeNum(snapshot?.analysis?.stats?.sl_count, 0)} />
                <Row label="BE" value={safeNum(snapshot?.analysis?.stats?.be_count, 0)} />
                <Row label="Winrate %" value={safeNum(snapshot?.analysis?.stats?.winrate_pct, 0)} />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        gap: 10,
        padding: "8px 10px",
        borderRadius: 12,
        background: "rgba(0,0,0,0.03)",
        fontSize: 13,
      }}
    >
      <div style={{ opacity: 0.75 }}>{label}</div>
      <div style={{ fontWeight: 700, textAlign: "right" }}>{String(value)}</div>
    </div>
  );
}