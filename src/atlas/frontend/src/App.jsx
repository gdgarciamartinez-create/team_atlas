import React, { useEffect, useMemo, useState } from "react";
import AtlasChart from "./AtlasChart.jsx";

function clampInt(n, min, max, fallback) {
  const x = parseInt(n, 10);
  if (Number.isNaN(x)) return fallback;
  return Math.max(min, Math.min(max, x));
}

function DecisionCard({ snap }) {
  const state = snap?.state ?? "—";
  const side = snap?.side ?? "—";
  const symbol = snap?.symbol ?? "—";
  const tf = snap?.tf ?? "—";
  const price = snap?.price ?? "—";
  const zone = snap?.zone ?? null;
  const note = snap?.note ?? "—";
  const score = snap?.score ?? "—";

  return (
    <div style={styles.card}>
      <div style={styles.cardTitle}>DECISIÓN</div>

      <div style={styles.grid2}>
        <div style={styles.kv}>
          <div style={styles.k}>Estado</div>
          <div style={styles.vBig}>{state}</div>
        </div>
        <div style={styles.kv}>
          <div style={styles.k}>Lado</div>
          <div style={styles.vBig}>{side}</div>
        </div>
      </div>

      <div style={styles.hr} />

      <div style={styles.grid2}>
        <div style={styles.kv}>
          <div style={styles.k}>Symbol</div>
          <div style={styles.v}>{symbol}</div>
        </div>
        <div style={styles.kv}>
          <div style={styles.k}>TF</div>
          <div style={styles.v}>{tf}</div>
        </div>
        <div style={styles.kv}>
          <div style={styles.k}>Price</div>
          <div style={styles.v}>{price}</div>
        </div>
        <div style={styles.kv}>
          <div style={styles.k}>Zone</div>
          <div style={styles.v}>
            {Array.isArray(zone) ? `${zone[0]} - ${zone[1]}` : "—"}
          </div>
        </div>
        <div style={styles.kv}>
          <div style={styles.k}>Score</div>
          <div style={styles.v}>{score}</div>
        </div>
        <div style={styles.kv}>
          <div style={styles.k}>Note</div>
          <div style={styles.v}>{note}</div>
        </div>
      </div>
    </div>
  );
}

function RawBox({ snap }) {
  return <pre style={styles.pre}>{snap ? JSON.stringify(snap, null, 2) : "—"}</pre>;
}

function SymbolList({ title, symbols, active, onPick }) {
  return (
    <div style={styles.card}>
      <div style={styles.cardTitle}>{title}</div>
      <div style={styles.symbolGrid}>
        {symbols.map((s) => {
          const isOn = s === active;
          return (
            <button
              key={s}
              onClick={() => onPick(s)}
              style={{ ...styles.symBtn, ...(isOn ? styles.symBtnOn : {}) }}
              title="Click para cambiar el gráfico"
            >
              {s}
            </button>
          );
        })}
      </div>
    </div>
  );
}

/**
 * ATLAS HUB:
 * - NO gráfico
 * - NO polling
 * - Solo decide a qué panel entrar: FOREX o SCALPING
 */
function AtlasHub({ onGoForex, onGoScalping }) {
  return (
    <div style={styles.hubWrap}>
      <div style={styles.hubCard}>
        <div style={styles.hubTitle}>ATLAS</div>
        <div style={styles.hubSub}>
          Hub maestro. Acá no hay gráfico ni snapshot. Solo elegís el modo.
        </div>

        <div style={{ height: 16 }} />

        <div style={styles.hubRow}>
          <button style={styles.hubBtn} onClick={onGoForex}>
            Entrar a FOREX
          </button>
          <button style={styles.hubBtn} onClick={onGoScalping}>
            Entrar a SCALPING
          </button>
        </div>

        <div style={{ height: 14 }} />
        <div style={styles.hubHint}>
          Después, el panel muestra el gráfico y la lista de símbolos clickeable.
        </div>
      </div>
    </div>
  );
}

export default function App() {
  // Universos (rápido de editar)
  const FOREX_SYMBOLS = useMemo(
    () => [
      "EURUSDz",
      "GBPUSDz",
      "USDJPYz",
      "USDCHFz",
      "AUDUSDz",
      "USDCADz",
      "NZDUSDz",
      "XAUUSDz",
      "BTCUSDz",
    ],
    []
  );

  // ✅ SCALPING: agregamos NASDAQ + PETRÓLEO (según tus símbolos MT5)
  const SCALPING_SYMBOLS = useMemo(
    () => [
      "EURUSDz",
      "GBPUSDz",
      "USDJPYz",
      "AUDUSDz",
      "USDCADz",
      "XAUUSDz",
      "USTECz",   // NASDAQ
      "USOILz",   // Petróleo
      "BTCUSDz",
    ],
    []
  );

  // Worlds reales
  // ATLAS_HUB no pega al backend, es solo UI.
  const [selectedWorld, setSelectedWorld] = useState("ATLAS_HUB"); // ATLAS_HUB | FOREX | SCALPING | GAP | GATILLO | PRESESION | BITACORA
  const [symbol, setSymbol] = useState("BTCUSDz");

  // TF para el mundo activo
  const [tf, setTf] = useState("M5");
  const [count, setCount] = useState(220);
  const [pollMs, setPollMs] = useState(1200);

  // Solo para scalping: toggle interno M1/M5
  const [scalpingTf, setScalpingTf] = useState("M1");

  const [snap, setSnap] = useState(null);
  const [err, setErr] = useState(null);
  const [showRaw, setShowRaw] = useState(false);

  const isHub = selectedWorld === "ATLAS_HUB";

  const effectiveTf = useMemo(() => {
    if (selectedWorld === "SCALPING") return scalpingTf;
    return tf;
  }, [selectedWorld, tf, scalpingTf]);

  const url = useMemo(() => {
    if (isHub) return "";
    const params = new URLSearchParams();
    params.set("world", selectedWorld);
    params.set("symbol", symbol);
    params.set("tf", effectiveTf);
    params.set("count", String(count));
    return `/api/snapshot?${params.toString()}`;
  }, [isHub, selectedWorld, symbol, effectiveTf, count]);

  // Polling solo si NO es hub
  useEffect(() => {
    if (isHub) return;

    let alive = true;

    async function tick() {
      try {
        setErr(null);
        const r = await fetch(url);
        const j = await r.json();
        if (!alive) return;
        setSnap(j);
      } catch (e) {
        if (!alive) return;
        setErr(String(e?.message || e));
      }
    }

    tick();
    const t = setInterval(tick, clampInt(pollMs, 200, 10000, 1200));
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, [isHub, url, pollMs]);

  const leftButtons = [
    { key: "ATLAS_HUB", label: "ATLAS", sub: "Hub maestro (sin chart)", right: "MASTER" },
    { key: "FOREX", label: "FOREX", sub: "Panel Forex", right: "WORLD" },
    { key: "SCALPING", label: "SCALPING", sub: "Panel Scalping (M1/M5)", right: "WORLD" },
    { key: "GAP", label: "GAP", sub: "Snapshot del mundo", right: "WORLD" },
    { key: "GATILLO", label: "GATILLO", sub: "Snapshot del mundo", right: "WORLD" },
    { key: "PRESESION", label: "PRESESIÓN", sub: "Filtro previo NY", right: "WORLD" },
    { key: "BITACORA", label: "BITÁCORA", sub: "Log / paper trades", right: "LOG" },
  ];

  const title = useMemo(() => {
    if (isHub) return "ATLAS";
    return selectedWorld;
  }, [isHub, selectedWorld]);

  const symbolList = useMemo(() => {
    if (selectedWorld === "FOREX") return FOREX_SYMBOLS;
    if (selectedWorld === "SCALPING") return SCALPING_SYMBOLS;
    return [];
  }, [selectedWorld, FOREX_SYMBOLS, SCALPING_SYMBOLS]);

  // Acciones del hub (rápidas)
  const goForexFromHub = () => {
    setSelectedWorld("FOREX");
    setTf("M5");
    if (!FOREX_SYMBOLS.includes(symbol)) setSymbol("EURUSDz");
  };

  const goScalpingFromHub = () => {
    setSelectedWorld("SCALPING");
    setScalpingTf("M1");
    if (!SCALPING_SYMBOLS.includes(symbol)) setSymbol("EURUSDz");
  };

  return (
    <div style={styles.page}>
      <div style={styles.sidebar}>
        <div style={styles.brand}>
          <div style={styles.brandTop}>TEAM</div>
          <div style={styles.brandBot}>ATLAS</div>
        </div>

        <div style={{ height: 10 }} />

        {leftButtons.map((b) => {
          const active = selectedWorld === b.key;
          return (
            <button
              key={b.key}
              onClick={() => setSelectedWorld(b.key)}
              style={{ ...styles.sideBtn, ...(active ? styles.sideBtnActive : {}) }}
            >
              <div style={styles.sideBtnRow}>
                <div>
                  <div style={styles.sideBtnTitle}>{b.label}</div>
                  <div style={styles.sideBtnSub}>{b.sub}</div>
                </div>
                <div style={styles.pill}>{b.right}</div>
              </div>
            </button>
          );
        })}

        <div style={{ flex: 1 }} />

        <div style={styles.footerMini}>
          <div>Fuente: MT5 (sufijo z)</div>
          <div>Poll: {pollMs}ms · Count: {count}</div>
        </div>
      </div>

      <div style={styles.main}>
        <div style={styles.topbar}>
          <div style={styles.topbarLeft}>
            <div style={styles.h1}>{title}</div>
            <div style={styles.h2}>{isHub ? "Hub: sin chart/snapshot" : `En vivo · URL: ${url}`}</div>
            {err ? <div style={styles.err}>Error: {err}</div> : null}
          </div>

          {!isHub ? (
            <div style={styles.controls}>
              <div style={styles.ctrl}>
                <div style={styles.ctrlLabel}>Symbol</div>
                <input style={styles.input} value={symbol} onChange={(e) => setSymbol(e.target.value)} />
              </div>

              {/* TF: en scalping va con toggle M1/M5 */}
              {selectedWorld === "SCALPING" ? (
                <div style={styles.ctrl}>
                  <div style={styles.ctrlLabel}>SCALPING TF</div>
                  <div style={styles.toggleRow}>
                    <button
                      onClick={() => setScalpingTf("M1")}
                      style={{ ...styles.toggleBtn, ...(scalpingTf === "M1" ? styles.toggleOn : {}) }}
                    >
                      M1
                    </button>
                    <button
                      onClick={() => setScalpingTf("M5")}
                      style={{ ...styles.toggleBtn, ...(scalpingTf === "M5" ? styles.toggleOn : {}) }}
                    >
                      M5
                    </button>
                  </div>
                </div>
              ) : (
                <div style={styles.ctrl}>
                  <div style={styles.ctrlLabel}>TF</div>
                  <select style={styles.select} value={tf} onChange={(e) => setTf(e.target.value)}>
                    <option value="M1">M1</option>
                    <option value="M5">M5</option>
                    <option value="M15">M15</option>
                    <option value="H1">H1</option>
                    <option value="H4">H4</option>
                    <option value="D1">D1</option>
                  </select>
                </div>
              )}

              <div style={styles.ctrl}>
                <div style={styles.ctrlLabel}>Count</div>
                <input
                  style={styles.input}
                  value={count}
                  onChange={(e) => setCount(clampInt(e.target.value, 20, 500, 220))}
                />
              </div>

              <div style={styles.ctrl}>
                <div style={styles.ctrlLabel}>Poll (ms)</div>
                <input
                  style={styles.input}
                  value={pollMs}
                  onChange={(e) => setPollMs(clampInt(e.target.value, 200, 10000, 1200))}
                />
              </div>
            </div>
          ) : null}
        </div>

        {isHub ? (
          <AtlasHub onGoForex={goForexFromHub} onGoScalping={goScalpingFromHub} />
        ) : (
          <div style={styles.body}>
            <div style={styles.chartWrap}>
              <div style={styles.cardTitle}>CHART</div>
              <div style={styles.chartInner}>
                <AtlasChart candles={snap?.candles || []} />
              </div>

              {symbolList.length ? (
                <div style={{ marginTop: 12 }}>
                  <SymbolList title="SYMBOLS" symbols={symbolList} active={symbol} onPick={setSymbol} />
                </div>
              ) : null}
            </div>

            <div style={styles.right}>
              <DecisionCard snap={snap} />

              <div style={{ height: 10 }} />

              <div style={styles.card}>
                <div style={styles.cardTitle}>Detalles técnicos</div>
                <div style={styles.row}>
                  <button style={styles.smallBtn} onClick={() => setShowRaw((x) => !x)}>
                    {showRaw ? "Ocultar Raw snapshot" : "Ver Raw snapshot"}
                  </button>
                </div>
                {showRaw ? <RawBox snap={snap} /> : null}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

const styles = {
  page: {
    height: "100vh",
    display: "flex",
    background: "#0b0f14",
    color: "rgba(255,255,255,0.92)",
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif",
  },
  sidebar: {
    width: 260,
    padding: 14,
    borderRight: "1px solid rgba(255,255,255,0.08)",
    display: "flex",
    flexDirection: "column",
  },
  brand: {
    padding: 14,
    borderRadius: 14,
    background: "rgba(255,255,255,0.04)",
    border: "1px solid rgba(255,255,255,0.06)",
  },
  brandTop: { fontSize: 12, opacity: 0.7, letterSpacing: 1 },
  brandBot: { fontSize: 18, fontWeight: 900, letterSpacing: 1 },

  sideBtn: {
    width: "100%",
    textAlign: "left",
    border: "1px solid rgba(255,255,255,0.06)",
    background: "rgba(255,255,255,0.03)",
    borderRadius: 14,
    padding: 12,
    marginBottom: 10,
    cursor: "pointer",
  },
  sideBtnActive: {
    background: "rgba(255,255,255,0.06)",
    border: "1px solid rgba(255,255,255,0.12)",
  },
  sideBtnRow: { display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 },
  sideBtnTitle: { fontSize: 13, fontWeight: 900 },
  sideBtnSub: { fontSize: 11, opacity: 0.65, marginTop: 2 },
  pill: {
    fontSize: 11,
    padding: "5px 9px",
    borderRadius: 999,
    background: "rgba(255,255,255,0.08)",
    border: "1px solid rgba(255,255,255,0.10)",
  },

  footerMini: {
    fontSize: 11,
    opacity: 0.65,
    padding: 10,
    borderRadius: 12,
    border: "1px solid rgba(255,255,255,0.06)",
    background: "rgba(255,255,255,0.03)",
  },

  main: { flex: 1, display: "flex", flexDirection: "column" },
  topbar: {
    display: "flex",
    alignItems: "flex-start",
    justifyContent: "space-between",
    padding: 14,
    borderBottom: "1px solid rgba(255,255,255,0.08)",
    gap: 14,
  },
  topbarLeft: { minWidth: 320 },
  h1: { fontSize: 16, fontWeight: 950 },
  h2: { fontSize: 12, opacity: 0.65, marginTop: 4 },
  err: { marginTop: 8, fontSize: 12, color: "rgba(255,120,120,0.95)" },

  controls: { display: "flex", gap: 10, flexWrap: "wrap", justifyContent: "flex-end" },
  ctrl: { display: "flex", flexDirection: "column", gap: 6, minWidth: 140 },
  ctrlLabel: { fontSize: 11, opacity: 0.7 },
  input: {
    borderRadius: 10,
    padding: "8px 10px",
    border: "1px solid rgba(255,255,255,0.10)",
    background: "rgba(255,255,255,0.04)",
    color: "rgba(255,255,255,0.92)",
  },
  select: {
    borderRadius: 10,
    padding: "8px 10px",
    border: "1px solid rgba(255,255,255,0.10)",
    background: "rgba(255,255,255,0.04)",
    color: "rgba(255,255,255,0.92)",
  },

  toggleRow: { display: "flex", gap: 8 },
  toggleBtn: {
    borderRadius: 10,
    padding: "8px 10px",
    border: "1px solid rgba(255,255,255,0.10)",
    background: "rgba(255,255,255,0.04)",
    color: "rgba(255,255,255,0.92)",
    cursor: "pointer",
    fontWeight: 900,
  },
  toggleOn: {
    background: "rgba(255,255,255,0.10)",
    border: "1px solid rgba(255,255,255,0.20)",
  },

  body: { flex: 1, display: "grid", gridTemplateColumns: "1fr 320px", gap: 14, padding: 14 },
  chartWrap: {
    borderRadius: 16,
    border: "1px solid rgba(255,255,255,0.08)",
    background: "rgba(255,255,255,0.03)",
    padding: 12,
    display: "flex",
    flexDirection: "column",
  },
  chartInner: { flex: 1, minHeight: 420, borderRadius: 12, overflow: "hidden" },

  right: { display: "flex", flexDirection: "column" },
  card: {
    borderRadius: 16,
    border: "1px solid rgba(255,255,255,0.08)",
    background: "rgba(255,255,255,0.03)",
    padding: 12,
  },
  cardTitle: { fontSize: 12, opacity: 0.7, fontWeight: 900, marginBottom: 10, letterSpacing: 0.5 },
  grid2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 },
  kv: { padding: 10, borderRadius: 12, border: "1px solid rgba(255,255,255,0.06)", background: "rgba(0,0,0,0.18)" },
  k: { fontSize: 11, opacity: 0.65 },
  v: { fontSize: 12, marginTop: 4 },
  vBig: { fontSize: 16, marginTop: 4, fontWeight: 950 },
  hr: { height: 1, background: "rgba(255,255,255,0.08)", margin: "12px 0" },

  row: { display: "flex", gap: 8, alignItems: "center" },
  smallBtn: {
    borderRadius: 10,
    padding: "8px 10px",
    border: "1px solid rgba(255,255,255,0.10)",
    background: "rgba(255,255,255,0.04)",
    color: "rgba(255,255,255,0.92)",
    cursor: "pointer",
    fontWeight: 900,
  },
  pre: {
    marginTop: 10,
    padding: 10,
    borderRadius: 12,
    background: "rgba(0,0,0,0.35)",
    border: "1px solid rgba(255,255,255,0.08)",
    fontSize: 11,
    maxHeight: 260,
    overflow: "auto",
  },

  hubWrap: { flex: 1, display: "grid", placeItems: "center", padding: 20 },
  hubCard: {
    width: "min(720px, 92vw)",
    borderRadius: 18,
    border: "1px solid rgba(255,255,255,0.10)",
    background: "rgba(255,255,255,0.04)",
    padding: 22,
  },
  hubTitle: { fontSize: 22, fontWeight: 980, letterSpacing: 1 },
  hubSub: { fontSize: 12, opacity: 0.7, marginTop: 6 },
  hubRow: { display: "flex", gap: 10, flexWrap: "wrap" },
  hubBtn: {
    borderRadius: 14,
    padding: "12px 14px",
    border: "1px solid rgba(255,255,255,0.14)",
    background: "rgba(255,255,255,0.06)",
    color: "rgba(255,255,255,0.92)",
    cursor: "pointer",
    fontWeight: 980,
  },
  hubHint: { fontSize: 12, opacity: 0.65 },

  symbolGrid: { display: "flex", flexWrap: "wrap", gap: 8 },
  symBtn: {
    borderRadius: 999,
    padding: "8px 10px",
    border: "1px solid rgba(255,255,255,0.10)",
    background: "rgba(255,255,255,0.04)",
    color: "rgba(255,255,255,0.92)",
    cursor: "pointer",
    fontSize: 12,
    fontWeight: 900,
  },
  symBtnOn: {
    background: "rgba(255,255,255,0.10)",
    border: "1px solid rgba(255,255,255,0.20)",
  },
};