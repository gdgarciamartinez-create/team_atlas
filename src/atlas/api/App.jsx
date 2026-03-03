import React, { useEffect, useMemo, useState } from "react";
import Charts from "./Charts.jsx";

/**
 * WORLDS / MÓDULOS
 * - Nota: tu backend usa `strategy` con keys (world.key).
 */
const WORLDS = [
  { key: "GATILLOS", label: "GATILLO" },
  { key: "ATLAS_IA", label: "ATLAS IA" },
  { key: "GAP", label: "GAP" },
  { key: "PRESESION", label: "PRESESIÓN" },
  { key: "VIVO", label: "VIVO" },
  { key: "BITACORA", label: "BITÁCORA" },
  { key: "OPERACIONES", label: "OPERACIONES" },
];

// TFs permitidos por mundo (según tus reglas)
function tfOptionsForWorld(world, atlasMode) {
  if (world === "GATILLOS") return ["M1", "M3", "M5", "M15"];
  if (world === "PRESESION") return ["M3", "M5"];
  if (world === "GAP") return ["M3", "M5"];
  if (world === "ATLAS_IA") {
    if (atlasMode === "FOREX") return ["M15", "M30", "H1", "H2"];
    return ["M1", "M3", "M5", "M15"];
  }
  return ["M1", "M3", "M5", "M15", "M30", "H1"];
}

function worldUsesCount(world) {
  if (world === "VIVO" || world === "BITACORA" || world === "OPERACIONES") return true;
  return false;
}

function worldNeedsSide(world) {
  return world === "GATILLOS";
}

function worldNeedsRange(world) {
  return world === "GATILLOS";
}

function safeJson(x) {
  try {
    return JSON.stringify(x, null, 2);
  } catch {
    return String(x);
  }
}

function badgeStyle(color) {
  return {
    display: "inline-flex",
    alignItems: "center",
    gap: 8,
    padding: "6px 10px",
    borderRadius: 999,
    border: `2px solid ${color}`,
    fontWeight: 800,
    fontSize: 12,
    background: "rgba(255,255,255,0.04)",
  };
}

function semaforoFromAnalysis(analysis) {
  const action = analysis?.action || analysis?.status || "WAIT";
  if (action === "SIGNAL" || action === "TRADE") return { label: action, color: "#00d37a" };
  if (action === "WAIT" || action === "NO_TRADE") return { label: action, color: "#ffcc00" };
  return { label: action, color: "#ff4d4d" };
}

// Helpers seguros para tipos
function asArray(x) {
  return Array.isArray(x) ? x : [];
}
function asString(x) {
  return typeof x === "string" ? x : "";
}

export default function App() {
  const [symbol, setSymbol] = useState("XAUUSDz");
  const [world, setWorld] = useState("GATILLOS");

  const [atlasMode, setAtlasMode] = useState("SCALPING"); // SCALPING | FOREX
  const [tf, setTf] = useState("M5");
  const [count, setCount] = useState(200);

  const [side, setSide] = useState("BUY");
  const [low, setLow] = useState("");
  const [high, setHigh] = useState("");

  const [snap, setSnap] = useState(null);
  const [rep, setRep] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    const options = tfOptionsForWorld(world, atlasMode);
    if (!options.includes(tf)) setTf(options[0]);
  }, [world, atlasMode]); // eslint-disable-line react-hooks/exhaustive-deps

  const snapUrl = useMemo(() => {
    const params = new URLSearchParams({
      symbol,
      tf,
      strategy: world,
    });

    if (worldUsesCount(world)) params.set("count", String(count));
    if (worldNeedsSide(world)) params.set("side", side);

    if (worldNeedsRange(world)) {
      if (low !== "") params.set("low", String(low));
      if (high !== "") params.set("high", String(high));
    }

    if (world === "ATLAS_IA") params.set("atlas_mode", atlasMode);

    return `/api/snapshot?${params.toString()}`;
  }, [symbol, tf, count, world, side, low, high, atlasMode]);

  const reportsUrl = useMemo(() => {
    const params = new URLSearchParams({ strategy: world });
    if (world === "ATLAS_IA") params.set("atlas_mode", atlasMode);
    return `/api/reports?${params.toString()}`;
  }, [world, atlasMode]);

  useEffect(() => {
    let alive = true;

    async function tick() {
      try {
        // SNAPSHOT
        const r1 = await fetch(snapUrl);
        if (!r1.ok) {
          const t = await r1.text().catch(() => "");
          if (!alive) return;
          setErr(`snapshot HTTP ${r1.status} ${r1.statusText}${t ? ` | ${t.slice(0, 120)}` : ""}`);
          return;
        }
        const j1 = await r1.json();
        if (!alive) return;
        setSnap(j1);

        // last_error puede venir como string o array, lo dejamos en string legible
        const le = j1?.last_error;
        if (Array.isArray(le)) setErr(le.join(" "));
        else setErr(asString(le));

        // REPORTS (si no existe, NO rompemos)
        const r2 = await fetch(reportsUrl);
        if (!r2.ok) {
          if (!alive) return;
          setRep(null);
          return;
        }
        const j2 = await r2.json();
        if (!alive) return;
        setRep(j2);
      } catch (e) {
        if (!alive) return;
        setErr(String(e));
      }
    }

    tick();
    const id = setInterval(tick, 1500);

    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [snapUrl, reportsUrl]);

  const analysis = snap?.analysis || {};
  const uiRows = asArray(snap?.ui?.rows);
  const moduleReport = rep?.report || null;

  const sem = semaforoFromAnalysis(analysis);
  const tfOptions = useMemo(() => tfOptionsForWorld(world, atlasMode), [world, atlasMode]);

  const symbolHint = "Ej: XAUUSDz, EURUSDz, USDJPYz, USDCADz, USTECz, USOILz";

  // ✅ Panel text: si no es array, no hacemos join
  const panelLines = asArray(snap?.panel_text);
  const panelText = panelLines.join("\n");

  return (
    <div style={{ padding: 18, fontFamily: "system-ui, Arial", background: "#0b0f14", color: "#e9eef5", minHeight: "100vh" }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 12 }}>
        <div style={{ fontSize: 22, fontWeight: 900, letterSpacing: 0.5 }}>
          <span style={{ color: "#66ffb3" }}>●</span> TEAM ATLAS
        </div>
        <div style={{ opacity: 0.75, fontSize: 12 }}>
          Modo laboratorio. UI en español. Módulos por mundo.
        </div>
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 14, flexWrap: "wrap" }}>
        {WORLDS.map((w) => (
          <button
            key={w.key}
            onClick={() => setWorld(w.key)}
            style={{
              padding: "8px 12px",
              borderRadius: 999,
              border: "1px solid rgba(255,255,255,0.12)",
              background: world === w.key ? "rgba(102,255,179,0.18)" : "rgba(255,255,255,0.03)",
              color: "#e9eef5",
              cursor: "pointer",
              fontWeight: 800,
            }}
          >
            {w.label}
          </button>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.05fr 1.15fr 0.9fr", gap: 14, marginBottom: 14 }}>
        <div style={{ border: "1px solid rgba(255,255,255,0.12)", borderRadius: 16, padding: 14, background: "rgba(255,255,255,0.02)" }}>
          <div style={{ fontWeight: 900, marginBottom: 10 }}>Laboratorio de ejecución</div>

          {world === "ATLAS_IA" ? (
            <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
              <button
                onClick={() => setAtlasMode("SCALPING")}
                style={{
                  flex: 1,
                  padding: "8px 10px",
                  borderRadius: 12,
                  border: "1px solid rgba(255,255,255,0.12)",
                  background: atlasMode === "SCALPING" ? "rgba(255,204,0,0.18)" : "rgba(255,255,255,0.03)",
                  color: "#e9eef5",
                  fontWeight: 900,
                  cursor: "pointer",
                }}
              >
                SCALPING
              </button>
              <button
                onClick={() => setAtlasMode("FOREX")}
                style={{
                  flex: 1,
                  padding: "8px 10px",
                  borderRadius: 12,
                  border: "1px solid rgba(255,255,255,0.12)",
                  background: atlasMode === "FOREX" ? "rgba(255,204,0,0.18)" : "rgba(255,255,255,0.03)",
                  color: "#e9eef5",
                  fontWeight: 900,
                  cursor: "pointer",
                }}
              >
                FOREX
              </button>
            </div>
          ) : null}

          <div style={{ display: "grid", gridTemplateColumns: "1.2fr 0.8fr", gap: 10 }}>
            <div>
              <div style={{ fontSize: 12, opacity: 0.75 }}>Símbolo (por ahora input)</div>
              <input
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                placeholder={symbolHint}
                style={{
                  width: "100%",
                  padding: "8px 10px",
                  borderRadius: 12,
                  border: "1px solid rgba(255,255,255,0.12)",
                  background: "rgba(0,0,0,0.35)",
                  color: "#e9eef5",
                  outline: "none",
                }}
              />
              <div style={{ fontSize: 11, opacity: 0.6, marginTop: 4 }}>
                Tip: usa sufijo <b>z</b> (XAUUSDz, EURUSDz, etc)
              </div>
            </div>

            <div>
              <div style={{ fontSize: 12, opacity: 0.75 }}>TF</div>
              <select
                value={tf}
                onChange={(e) => setTf(e.target.value)}
                style={{
                  width: "100%",
                  padding: "8px 10px",
                  borderRadius: 12,
                  border: "1px solid rgba(255,255,255,0.12)",
                  background: "rgba(0,0,0,0.35)",
                  color: "#e9eef5",
                  outline: "none",
                }}
              >
                {tfOptions.map((x) => (
                  <option key={x} value={x}>
                    {x}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {worldUsesCount(world) ? (
            <div style={{ marginTop: 10 }}>
              <div style={{ fontSize: 12, opacity: 0.75 }}>Velas (solo laboratorio)</div>
              <input
                type="number"
                value={count}
                onChange={(e) => setCount(Number(e.target.value))}
                style={{
                  width: "100%",
                  padding: "8px 10px",
                  borderRadius: 12,
                  border: "1px solid rgba(255,255,255,0.12)",
                  background: "rgba(0,0,0,0.35)",
                  color: "#e9eef5",
                  outline: "none",
                }}
                min={50}
                max={800}
              />
            </div>
          ) : null}

          {world === "GATILLOS" ? (
            <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: "0.7fr 0.65fr 0.65fr", gap: 10 }}>
              <div>
                <div style={{ fontSize: 12, opacity: 0.75 }}>Dirección</div>
                <select
                  value={side}
                  onChange={(e) => setSide(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 10px",
                    borderRadius: 12,
                    border: "1px solid rgba(255,255,255,0.12)",
                    background: "rgba(0,0,0,0.35)",
                    color: "#e9eef5",
                    outline: "none",
                  }}
                >
                  <option value="BUY">BUY</option>
                  <option value="SELL">SELL</option>
                </select>
              </div>
              <div>
                <div style={{ fontSize: 12, opacity: 0.75 }}>Low (precio)</div>
                <input
                  value={low}
                  onChange={(e) => setLow(e.target.value)}
                  placeholder="Ej: 4970.10"
                  style={{
                    width: "100%",
                    padding: "8px 10px",
                    borderRadius: 12,
                    border: "1px solid rgba(255,255,255,0.12)",
                    background: "rgba(0,0,0,0.35)",
                    color: "#e9eef5",
                    outline: "none",
                  }}
                />
              </div>
              <div>
                <div style={{ fontSize: 12, opacity: 0.75 }}>High (precio)</div>
                <input
                  value={high}
                  onChange={(e) => setHigh(e.target.value)}
                  placeholder="Ej: 4988.40"
                  style={{
                    width: "100%",
                    padding: "8px 10px",
                    borderRadius: 12,
                    border: "1px solid rgba(255,255,255,0.12)",
                    background: "rgba(0,0,0,0.35)",
                    color: "#e9eef5",
                    outline: "none",
                  }}
                />
              </div>
              <div style={{ gridColumn: "1 / -1", fontSize: 11, opacity: 0.65 }}>
                Tip: si MT5 está OK y no ves velas, casi siempre es mapeo de candles.
              </div>
            </div>
          ) : null}

          {err ? (
            <div style={{ marginTop: 10, fontSize: 12, color: "#ff6b6b" }}>
              last_error: {err}
            </div>
          ) : null}
        </div>

        <div style={{ border: "1px solid rgba(255,255,255,0.12)", borderRadius: 16, padding: 14, background: "rgba(255,255,255,0.02)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
            <div style={{ fontWeight: 900 }}>Estado (análisis)</div>
            <div style={{ fontSize: 12, opacity: 0.7 }}>{world}{world === "ATLAS_IA" ? ` • ${atlasMode}` : ""}</div>
          </div>

          <div style={{ marginBottom: 10 }}>
            <span style={badgeStyle(sem.color)}>● {sem.label}</span>
          </div>

          <div style={{ fontSize: 12, opacity: 0.9, lineHeight: 1.45 }}>
            {analysis?.side ? <div><b>Side:</b> {analysis.side}</div> : null}
            {analysis?.entry ? <div><b>Entry:</b> {analysis.entry}</div> : null}
            {analysis?.sl ? <div><b>SL:</b> {analysis.sl}</div> : null}
            {analysis?.tp ? <div><b>TP:</b> {analysis.tp}</div> : null}
            {analysis?.partial ? <div><b>Parcial:</b> {analysis.partial}</div> : null}
            {analysis?.lot_1pct_10k ? <div><b>Lot (1% 10k):</b> {analysis.lot_1pct_10k}</div> : null}
            {analysis?.reason ? (
              <div style={{ marginTop: 6, opacity: 0.75 }}>
                <b>Razón:</b> {analysis.reason}
              </div>
            ) : (
              <div style={{ marginTop: 6, opacity: 0.6 }}>
                Sin señal aún. (LAB: observa y calla)
              </div>
            )}
          </div>

          <div style={{ marginTop: 10, borderTop: "1px solid rgba(255,255,255,0.08)", paddingTop: 10 }}>
            <div style={{ fontWeight: 900, marginBottom: 6 }}>Reporte del módulo</div>
            {moduleReport ? (
              <pre style={{ margin: 0, fontSize: 12, whiteSpace: "pre-wrap", opacity: 0.85 }}>
{safeJson(moduleReport)}
              </pre>
            ) : (
              <div style={{ opacity: 0.7 }}>Sin reporte</div>
            )}
          </div>
        </div>

        <div style={{ border: "1px solid rgba(255,255,255,0.12)", borderRadius: 16, padding: 14, background: "rgba(255,255,255,0.02)" }}>
          <div style={{ fontWeight: 900, marginBottom: 10 }}>Panel (backend)</div>
          <pre style={{ margin: 0, fontSize: 12, whiteSpace: "pre-wrap", opacity: 0.85 }}>
{panelText}
          </pre>
        </div>
      </div>

      <div style={{ border: "1px solid rgba(255,255,255,0.12)", borderRadius: 16, padding: 14, background: "rgba(255,255,255,0.02)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 10 }}>
          <div style={{ fontWeight: 900 }}>Gráfico</div>
          <div style={{ fontSize: 12, opacity: 0.7 }}>
            Hora Chile: {snap?.meta?.tz || "America/Santiago (pendiente en backend)"}
          </div>
        </div>

        <Charts candles={asArray(snap?.candles)} />

        <div style={{ marginTop: 12 }}>
          <div style={{ fontWeight: 900, marginBottom: 8 }}>
            Lista de divisas (estado por renglón)
          </div>

          {uiRows.length ? (
            <div style={{ display: "grid", gap: 8 }}>
              {uiRows.map((r, idx) => {
                const rSem = semaforoFromAnalysis(r);
                return (
                  <div
                    key={`${r.symbol || "row"}-${idx}`}
                    style={{
                      display: "grid",
                      gridTemplateColumns: "160px 110px 1fr 42px",
                      gap: 10,
                      alignItems: "center",
                      padding: "10px 12px",
                      borderRadius: 14,
                      border: "1px solid rgba(255,255,255,0.10)",
                      background: "rgba(0,0,0,0.25)",
                    }}
                  >
                    <div style={{ fontWeight: 900 }}>
                      {r.symbol || "—"}
                      <div style={{ fontSize: 11, opacity: 0.6 }}>{r.tf || ""}</div>
                    </div>

                    <div>
                      <span style={badgeStyle(rSem.color)}>● {rSem.label}</span>
                    </div>

                    <div style={{ fontSize: 12, opacity: 0.85 }}>
                      {r.text || r.reason || "Sin detalle"}
                      {r.entry ? <span> • Entry {r.entry}</span> : null}
                      {r.sl ? <span> • SL {r.sl}</span> : null}
                      {r.tp ? <span> • TP {r.tp}</span> : null}
                    </div>

                    <button
                      title="Activar notificación Telegram (opcional)"
                      onClick={() => console.log("toggle telegram for", r.symbol, world)}
                      style={{
                        width: 38,
                        height: 38,
                        borderRadius: 12,
                        border: "1px solid rgba(255,255,255,0.12)",
                        background: "rgba(255,255,255,0.03)",
                        color: "#e9eef5",
                        cursor: "pointer",
                        fontSize: 18,
                        fontWeight: 900,
                      }}
                    >
                      🔔
                    </button>
                  </div>
                );
              })}
            </div>
          ) : (
            <div style={{ opacity: 0.65, fontSize: 12 }}>
              (Sin filas aún) Cuando el backend entregue <code>snap.ui.rows</code>, acá se verá el semáforo por divisa.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
