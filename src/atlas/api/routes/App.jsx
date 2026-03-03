import { useEffect, useMemo, useState } from "react";
import AtlasChart from "./AtlasChart";
import TradeLog from "./TradeLog";

const WORLDS = ["GAP", "PRESESIÓN", "GATILLO", "ATLAS IA", "BITACORA"];

const COLORS = {
  GAP: { bg: "#1b1506", accent: "#b8860b" },
  "PRESESIÓN": { bg: "#081826", accent: "#1d4ed8" },
  GATILLO: { bg: "#20090a", accent: "#dc2626" },
  "ATLAS IA": { bg: "#140a22", accent: "#7c3aed" },
  FOREX: { bg: "#071a10", accent: "#16a34a" },
  SCALPING: { bg: "#221105", accent: "#f97316" },
  BITACORA: { bg: "#0a1320", accent: "#e11d48" }, // elegante (no rosado chillón)
};

// ✅ PRESESIÓN (solo EUR*/USD* como dijiste)
const PRESESIÓN_PAIRS = [
  "EURUSDz", "EURJPYz", "EURAUDz", "EURCADz", "EURNZDz", "EURCHFz", "EURGBPz",
  "USDJPYz", "USDCADz", "USDCHFz",
];

// ✅ Universo completo para dropdown GATILLO (según tus fotos + mandamiento sufijo z)
const ALL_SYMBOLS = [
  "XAUUSDz",
  "USTEC_x100z",
  "USOILz",
  "BTCUSDz",

  "EURUSDz","EURJPYz","EURAUDz","EURCADz","EURNZDz","EURCHFz","EURGBPz",
  "USDJPYz","USDCADz","USDCHFz",

  "GBPUSDz","GBPCADz","GBPJPYz","GBPCHFz","GBPNZDz",
  "AUDUSDz","AUDJPYz","AUDCADz","AUDCHFz","AUDNZDz",
  "NZDUSDz","NZDJPYz","NZDCADz","NZDCHFz",
  "CHFJPYz","CADCHFz","CADJPYz",
];

// ✅ ATLAS IA listas cerradas (lo que pediste)
const ATLAS_SCALPING = ["XAUUSDz", "EURUSDz", "USOILz", "USTEC_x100z"];
const ATLAS_FOREX = ["XAUUSDz", "EURUSDz", "USDJPYz", "GBPUSDz"];

// ---- UI helpers ----
function Badge({ tone, text }) {
  const map = {
    TRADE: { bg: "#052e16", fg: "#86efac" },
    WAIT: { bg: "#1f1a05", fg: "#fde047" },
    NO_TRADE: { bg: "#2a0a0a", fg: "#fca5a5" },
    ERROR: { bg: "#111827", fg: "#cbd5e1" },
  };
  const s = map[tone] || map.ERROR;
  return (
    <span
      style={{
        padding: "4px 10px",
        borderRadius: 999,
        fontSize: 12,
        background: s.bg,
        color: s.fg,
        border: "1px solid rgba(255,255,255,0.10)",
        whiteSpace: "nowrap",
      }}
    >
      {text}
    </span>
  );
}

function Field({ label, children }) {
  return (
    <div style={{ display: "grid", gap: 6 }}>
      <div style={{ fontSize: 12, opacity: 0.75 }}>{label}</div>
      {children}
    </div>
  );
}

// ✅ Style para SELECT + OPTIONS (FIX del “blanco/blanco”)
const selectStyle = {
  width: "100%",
  padding: 10,
  borderRadius: 12,
  border: "1px solid rgba(255,255,255,0.12)",
  background: "rgba(255,255,255,0.06)",
  color: "#e5e7eb",
  outline: "none",
};

const optionStyle = {
  background: "#0b1220", // oscuro
  color: "#e5e7eb",
};

export default function App() {
  const [world, setWorld] = useState("GATILLO");
  const [island, setIsland] = useState("SCALPING");

  const [symbol, setSymbol] = useState("XAUUSDz");
  const [tf, setTf] = useState("M5");
  const [count, setCount] = useState(120);

  const [zoneLow, setZoneLow] = useState("");
  const [zoneHigh, setZoneHigh] = useState("");

  const [backendOnline, setBackendOnline] = useState(false);
  const [mt5Ok, setMt5Ok] = useState(false);
  const [mt5Error, setMt5Error] = useState("");

  const theme = COLORS[world] || { bg: "#0b1220", accent: "#60a5fa" };

  const atlasPairs = island === "SCALPING" ? ATLAS_SCALPING : ATLAS_FOREX;

  const pairsForList = useMemo(() => {
    if (world === "GAP") return ["XAUUSDz"];
    if (world === "PRESESIÓN") return PRESESIÓN_PAIRS;
    return [];
  }, [world]);

  // Defaults por mundo (sin apretar nada raro)
  useEffect(() => {
    if (world === "GAP") {
      setSymbol("XAUUSDz");
      setTf("M1");
      return;
    }
    if (world === "PRESESIÓN") {
      setSymbol("EURUSDz");
      setTf("M5");
      return;
    }
    if (world === "GATILLO") {
      setSymbol((p) => p || "XAUUSDz");
      setTf((p) => p || "M3");
      return;
    }
    if (world === "ATLAS IA") {
      setSymbol(atlasPairs[0] || "XAUUSDz");
      setTf("M5");
      return;
    }
    if (world === "BITACORA") {
      // no toca símbolo: bitácora es otra pantalla
      return;
    }
  }, [world]); // eslint-disable-line

  useEffect(() => {
    if (world === "ATLAS IA") setSymbol(atlasPairs[0] || "XAUUSDz");
  }, [island]); // eslint-disable-line

  // Poll snapshot (único) — backend decide si usa MT5 o no
  useEffect(() => {
    const t = setInterval(async () => {
      try {
        const qs = new URLSearchParams({
          world,
          symbol,
          tf,
          count: String(count),
        }).toString();

        const res = await fetch(`/api/snapshot?${qs}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        setBackendOnline(true);
        setMt5Ok(Boolean(data?.mt5?.ok));
        setMt5Error(data?.mt5?.last_error || data?.data?.last_error || "");
      } catch (e) {
        setBackendOnline(false);
        setMt5Ok(false);
        setMt5Error(String(e?.message || e));
      }
    }, 1200);

    return () => clearInterval(t);
  }, [world, symbol, tf, count]);

  function trafficTone(base = "WAIT") {
    if (!backendOnline) return "ERROR";
    if (!mt5Ok) return "ERROR";
    return base;
  }

  function atlasIdeaText() {
    return island === "SCALPING"
      ? "Reacción rápida en zona. TP1 temprano, BE rápido. Si no responde rápido, se aborta."
      : "Ideas 4H/1H con lectura limpia y timing en 5m/3m. No anticipar, esperar confirmación.";
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#0b1220",
        color: "#e5e7eb",
        fontFamily: "system-ui, -apple-system, Segoe UI, Roboto",
      }}
    >
      {/* TopBar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "14px 18px",
          borderBottom: "1px solid rgba(255,255,255,0.06)",
          background: "rgba(0,0,0,0.25)",
          gap: 12,
          flexWrap: "wrap",
        }}
      >
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <div
            style={{
              width: 10,
              height: 10,
              borderRadius: 999,
              background: backendOnline ? "#22c55e" : "#ef4444",
            }}
          />
          <div style={{ fontWeight: 900, letterSpacing: 0.6 }}>TEAM ATLAS</div>
          <div style={{ opacity: 0.65, fontSize: 12 }}>
            Backend: {backendOnline ? "ONLINE" : "OFFLINE"} • MT5: {mt5Ok ? "OK" : "OFF"} • símbolos con sufijo z
          </div>
        </div>
        <div style={{ opacity: 0.8, fontSize: 12, maxWidth: 560, textAlign: "right" }}>
          {mt5Ok ? "MT5 conectado" : mt5Error ? `MT5: ${mt5Error}` : "MT5 sin datos"}
        </div>
      </div>

      {/* World Tabs */}
      <div style={{ padding: 18, display: "flex", gap: 10, flexWrap: "wrap" }}>
        {WORLDS.map((w) => {
          const active = w === world;
          const c = COLORS[w];
          return (
            <button
              key={w}
              onClick={() => setWorld(w)}
              style={{
                padding: "10px 14px",
                borderRadius: 14,
                border: "1px solid rgba(255,255,255,0.10)",
                background: active ? c?.accent : "rgba(255,255,255,0.05)",
                color: "white",
                cursor: "pointer",
                fontWeight: 900,
              }}
            >
              {w}
            </button>
          );
        })}
      </div>

      {/* Main layout: más ancho a la izquierda para que GATILLO NO quede apretado */}
      <div
        style={{
          padding: 18,
          display: "grid",
          gridTemplateColumns: "440px 1fr", // ✅ antes 360px → ahora entra cómodo
          gap: 16,
        }}
      >
        {/* Left Panel */}
        <div
          style={{
            borderRadius: 16,
            border: "1px solid rgba(255,255,255,0.10)",
            overflow: "hidden",
            background: theme.bg,
          }}
        >
          <div
            style={{
              padding: 14,
              borderBottom: "1px solid rgba(255,255,255,0.10)",
              background: "rgba(0,0,0,0.25)",
            }}
          >
            <div style={{ fontSize: 12, opacity: 0.7 }}>Mundo</div>
            <div style={{ fontSize: 18, fontWeight: 950, color: theme.accent }}>{world}</div>
          </div>

          <div style={{ padding: 14, display: "grid", gap: 14 }}>
            {/* ✅ BITACORA como mundo real */}
            {world === "BITACORA" && (
              <div style={{ display: "grid", gap: 10 }}>
                <div style={{ fontWeight: 950, fontSize: 16 }}>Bitácora</div>
                <div style={{ opacity: 0.8, fontSize: 13 }}>
                  Este mundo es pantalla completa. Acá después metemos:
                  <ul style={{ marginTop: 8, paddingLeft: 18, lineHeight: 1.4 }}>
                    <li>Conteo total / winrate / R promedio</li>
                    <li>Operaciones por símbolo y por mundo</li>
                    <li>Export a Excel (más adelante)</li>
                  </ul>
                </div>
                <div style={{ opacity: 0.7, fontSize: 12 }}>
                  Por ahora: estructura lista. Cuando el motor empiece a escribir logs, acá se ve todo.
                </div>
              </div>
            )}

            {world === "GATILLO" && (
              <div style={{ display: "grid", gap: 12 }}>
                <div style={{ fontWeight: 950 }}>Laboratorio de ejecución</div>

                <Field label="Símbolo (dropdown completo)">
                  <select value={symbol} onChange={(e) => setSymbol(e.target.value)} style={selectStyle}>
                    {ALL_SYMBOLS.map((s) => (
                      <option key={s} value={s} style={optionStyle}>
                        {s}
                      </option>
                    ))}
                  </select>
                </Field>

                {/* ✅ Más aire: 2 columnas pero sin apretar */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                  <Field label="TF">
                    <select value={tf} onChange={(e) => setTf(e.target.value)} style={selectStyle}>
                      {["M1", "M3", "M5", "M15"].map((x) => (
                        <option key={x} style={optionStyle}>
                          {x}
                        </option>
                      ))}
                    </select>
                  </Field>

                  <Field label="Velas (count)">
                    <input
                      type="number"
                      value={count}
                      onChange={(e) => setCount(Number(e.target.value))}
                      style={selectStyle}
                    />
                  </Field>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                  <Field label="Low (zona)">
                    <input
                      value={zoneLow}
                      onChange={(e) => setZoneLow(e.target.value)}
                      placeholder="ej: 1982.10"
                      style={selectStyle}
                    />
                  </Field>

                  <Field label="High (zona)">
                    <input
                      value={zoneHigh}
                      onChange={(e) => setZoneHigh(e.target.value)}
                      placeholder="ej: 1988.40"
                      style={selectStyle}
                    />
                  </Field>
                </div>

                <div style={{ opacity: 0.75, fontSize: 12 }}>
                  Semáforo hoy es mínimo (conexión). La lógica TRADE/NO_TRADE la enchufamos cuando el motor decida.
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ fontWeight: 900 }}>Estado</div>
                  <Badge tone={trafficTone("WAIT")} text={trafficTone("WAIT")} />
                </div>

                <TradeLog defaultWorld={world} defaultSymbol={symbol} />
              </div>
            )}

            {world === "GAP" && (
              <div style={{ display: "grid", gap: 8 }}>
                <div style={{ fontWeight: 950 }}>GAP XAUUSD</div>
                <div style={{ opacity: 0.85, fontSize: 13 }}>
                  Par fijo: <b>XAUUSDz</b>
                </div>
                <div style={{ opacity: 0.85, fontSize: 13 }}>
                  TF fijo: <b>M1</b>
                </div>
                <div style={{ opacity: 0.7, fontSize: 12 }}>
                  Sin parámetros acá. Solo lectura del estado y ritual.
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 6 }}>
                  <div style={{ fontWeight: 900 }}>Semáforo</div>
                  <Badge tone={trafficTone("WAIT")} text={trafficTone("WAIT")} />
                </div>
              </div>
            )}

            {world === "PRESESIÓN" && (
              <div style={{ display: "grid", gap: 10 }}>
                <div style={{ fontWeight: 950 }}>PRESESIÓN</div>
                <div style={{ opacity: 0.7, fontSize: 12 }}>
                  Lista fija EUR*/USD*. Click en un par para abrir gráfico.
                </div>

                <Field label="TF (solo para mirar llegada)">
                  <select value={tf} onChange={(e) => setTf(e.target.value)} style={selectStyle}>
                    {["M3", "M5"].map((x) => (
                      <option key={x} style={optionStyle}>
                        {x}
                      </option>
                    ))}
                  </select>
                </Field>

                <div style={{ display: "grid", gap: 8 }}>
                  {pairsForList.map((p) => (
                    <button
                      key={p}
                      onClick={() => setSymbol(p)}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        padding: "10px 12px",
                        borderRadius: 12,
                        border: "1px solid rgba(255,255,255,0.10)",
                        background: p === symbol ? "rgba(255,255,255,0.07)" : "rgba(255,255,255,0.04)",
                        color: "white",
                        cursor: "pointer",
                      }}
                    >
                      <span style={{ fontWeight: 900 }}>{p}</span>
                      <Badge tone={trafficTone("WAIT")} text={trafficTone("WAIT")} />
                    </button>
                  ))}
                </div>

                <TradeLog defaultWorld={world} defaultSymbol={symbol} />
              </div>
            )}

            {world === "ATLAS IA" && (
              <div style={{ display: "grid", gap: 12 }}>
                <div style={{ fontWeight: 950 }}>ATLAS IA</div>

                <div style={{ display: "flex", gap: 10 }}>
                  {["SCALPING", "FOREX"].map((k) => {
                    const active = island === k;
                    return (
                      <button
                        key={k}
                        onClick={() => setIsland(k)}
                        style={{
                          flex: 1,
                          padding: "10px 10px",
                          borderRadius: 12,
                          border: "1px solid rgba(255,255,255,0.10)",
                          background: active ? COLORS[k].accent : "rgba(255,255,255,0.05)",
                          color: "white",
                          fontWeight: 950,
                          cursor: "pointer",
                        }}
                      >
                        {k}
                      </button>
                    );
                  })}
                </div>

                <div
                  style={{
                    borderRadius: 12,
                    border: "1px solid rgba(255,255,255,0.10)",
                    background: COLORS[island].bg,
                    padding: 12,
                  }}
                >
                  <div style={{ fontWeight: 950, color: COLORS[island].accent }}>{island}: 4 pares</div>
                  <div style={{ opacity: 0.75, fontSize: 12, marginTop: 6 }}>Reseña: {atlasIdeaText()}</div>

                  <div style={{ display: "grid", gap: 8, marginTop: 10 }}>
                    {atlasPairs.map((p) => (
                      <button
                        key={p}
                        onClick={() => setSymbol(p)}
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          padding: "10px 12px",
                          borderRadius: 12,
                          border: "1px solid rgba(255,255,255,0.10)",
                          background: p === symbol ? "rgba(255,255,255,0.10)" : "rgba(255,255,255,0.04)",
                          color: "white",
                          cursor: "pointer",
                        }}
                      >
                        <span style={{ fontWeight: 950 }}>{p}</span>
                        <Badge tone={trafficTone("WAIT")} text={trafficTone("WAIT")} />
                      </button>
                    ))}
                  </div>
                </div>

                <TradeLog defaultWorld={`ATLAS IA - ${island}`} defaultSymbol={symbol} />
              </div>
            )}
          </div>
        </div>

        {/* Right Panel */}
        <div
          style={{
            borderRadius: 16,
            border: "1px solid rgba(255,255,255,0.10)",
            background: "rgba(255,255,255,0.03)",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              padding: 14,
              borderBottom: "1px solid rgba(255,255,255,0.10)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: 12,
              flexWrap: "wrap",
            }}
          >
            <div>
              <div style={{ fontWeight: 950, fontSize: 16 }}>
                {symbol} <span style={{ opacity: 0.6 }}>({tf})</span>
              </div>
              <div style={{ fontSize: 12, opacity: 0.65 }}>
                Velas reales MT5. Si MT5 no responde, el chart queda vacío (sin inventar).
              </div>
            </div>

            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
              <div style={{ opacity: 0.75, fontSize: 12 }}>Velas: {count}</div>
              <Badge tone={trafficTone("WAIT")} text={trafficTone("WAIT")} />
            </div>
          </div>

          <div style={{ padding: 12 }}>
            <AtlasChart symbol={symbol} tf={tf} count={count} />
          </div>
        </div>
      </div>

      {/* Responsive: si pantalla chica, que no explote */}
      <style>{`
        @media (max-width: 980px) {
          .atlas-grid { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </div>
  );
}