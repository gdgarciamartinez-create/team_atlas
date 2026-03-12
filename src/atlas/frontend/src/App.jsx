import { useEffect, useMemo, useRef, useState } from "react";
import Charts from "./Charts";

const WORLDS = [
  { value: "ATLAS_IA", label: "ATLAS_IA", color: "#ff2fb3" },
  { value: "PRESESION", label: "PRESESION", color: "#f0b35a" },
  { value: "GAP", label: "GAP", color: "#63c787" },
  { value: "BITACORA", label: "BITACORA", color: "#b784ff" },
];

const ATLAS_MODES = [
  { value: "SCALPING_M1", label: "SCALPING M1" },
  { value: "SCALPING_M5", label: "SCALPING M5" },
  { value: "FOREX", label: "FOREX" },
];

const BITACORA_MODES = [
  { value: "SCALPING_M1", label: "SCALPING M1" },
  { value: "SCALPING_M5", label: "SCALPING M5" },
  { value: "FOREX", label: "FOREX" },
];

const SYMBOLS_BY_WORLD = {
  ATLAS_IA: [
    "XAUUSDz",
    "EURUSDz",
    "GBPUSDz",
    "USDJPYz",
    "USDCHFz",
    "USDCADz",
    "AUDUSDz",
    "NZDUSDz",
    "EURJPYz",
    "EURGBPz",
    "EURCADz",
    "EURAUDz",
    "GBPNZDz",
    "BTCUSDz",
    "USTECz",
    "USOILz",
  ],
  PRESESION: [
    "EURUSDz",
    "GBPUSDz",
    "AUDUSDz",
    "NZDUSDz",
    "USDJPYz",
    "USDCHFz",
    "USDCADz",
    "EURJPYz",
    "EURGBPz",
    "EURCADz",
    "EURAUDz",
  ],
  GAP: ["XAUUSDz"],
  BITACORA: [],
};

const STATE_COLORS = {
  SIN_SETUP: "#6b7280",
  SET_UP: "#f0b35a",
  ENTRY: "#f28c38",
  IN_TRADE: "#5da8ff",
  TP1: "#63c787",
  TP2: "#2fbf71",
  RUN: "#b784ff",
  CLOSED: "#ffffff",
};

function withAlpha(hexColor, alpha) {
  const map = {
    "#ff2fb3": `rgba(255,47,179,${alpha})`,
    "#5da8ff": `rgba(93,168,255,${alpha})`,
    "#f0b35a": `rgba(240,179,90,${alpha})`,
    "#63c787": `rgba(99,199,135,${alpha})`,
    "#b784ff": `rgba(183,132,255,${alpha})`,
    "#9fb3c8": `rgba(159,179,200,${alpha})`,
    "#f28c38": `rgba(242,140,56,${alpha})`,
    "#6b7280": `rgba(107,114,128,${alpha})`,
    "#2fbf71": `rgba(47,191,113,${alpha})`,
    "#ffffff": `rgba(255,255,255,${alpha})`,
    "#ff6b6b": `rgba(255,107,107,${alpha})`,
  };
  return map[hexColor] || `rgba(255,47,179,${alpha})`;
}

function modeAccent(atlasMode) {
  return atlasMode === "FOREX" ? "#5da8ff" : "#ff2fb3";
}

function decimalsBySymbol(sym) {
  if (!sym) return 5;
  if (sym.startsWith("XAU")) return 2;
  if (sym.startsWith("BTC")) return 2;
  if (sym.startsWith("USTEC")) return 2;
  if (sym.startsWith("USOIL")) return 2;
  if (sym.includes("JPY")) return 3;
  return 5;
}

function formatNumber(v, digits = 2) {
  if (v === null || v === undefined || v === "") return "-";
  const n = Number(v);
  if (!Number.isFinite(n)) return "-";
  return n.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function formatSigned(v, digits = 2) {
  if (v === null || v === undefined || v === "") return "-";
  const n = Number(v);
  if (!Number.isFinite(n)) return "-";
  const out = n.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
  return n > 0 ? `+${out}` : out;
}

function tfForWorld(world, atlasMode) {
  if (world === "GAP") return "M1";
  if (world === "PRESESION") return "M5";
  if (world === "ATLAS_IA") {
    if (atlasMode === "SCALPING_M1") return "M1";
    if (atlasMode === "SCALPING_M5") return "M5";
    if (atlasMode === "FOREX") return "H1";
  }
  return "-";
}

async function fetchJson(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) {
    const err = new Error(`HTTP ${res.status}`);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

function normalizeStateKey(state) {
  const s = String(state || "").toUpperCase().trim();

  if (s === "WAIT" || s === "NO_DATA" || s === "UNKNOWN_MODE" || s === "UNKNOWN_WORLD") {
    return "SIN_SETUP";
  }

  if (s === "WAIT_GATILLO" || s === "SIGNAL" || s === "SETUP") {
    return "SET_UP";
  }

  if (s === "SIN_SETUP") return "SIN_SETUP";
  if (s === "SET_UP") return "SET_UP";
  if (s === "ENTRY") return "ENTRY";
  if (s === "IN_TRADE") return "IN_TRADE";
  if (s === "TP1") return "TP1";
  if (s === "TP2") return "TP2";
  if (s === "RUN") return "RUN";
  if (s === "CLOSED") return "CLOSED";

  return "SIN_SETUP";
}

function stateLabel(state) {
  const s = normalizeStateKey(state);
  if (s === "SIN_SETUP") return "SIN SETUP";
  if (s === "SET_UP") return "SET UP";
  if (s === "IN_TRADE") return "IN TRADE";
  return s;
}

function getStateColor(state) {
  return STATE_COLORS[normalizeStateKey(state)] || "#6b7280";
}

function stateBadgeStyle(state) {
  const s = normalizeStateKey(state);

  if (s === "SET_UP") {
    return {
      ...styles.badgeBase,
      background: "rgba(240, 179, 90, 0.14)",
      border: "1px solid rgba(240, 179, 90, 0.30)",
      color: "#eadfb7",
    };
  }

  if (s === "ENTRY") {
    return {
      ...styles.badgeBase,
      background: "rgba(242, 140, 56, 0.16)",
      border: "1px solid rgba(242, 140, 56, 0.34)",
      color: "#ffe2c4",
    };
  }

  if (s === "IN_TRADE") {
    return {
      ...styles.badgeBase,
      background: "rgba(93, 168, 255, 0.18)",
      border: "1px solid rgba(93, 168, 255, 0.34)",
      color: "#d9e7ff",
    };
  }

  if (s === "TP1") {
    return {
      ...styles.badgeBase,
      background: "rgba(99, 199, 135, 0.16)",
      border: "1px solid rgba(99, 199, 135, 0.34)",
      color: "#d8ffe6",
    };
  }

  if (s === "TP2") {
    return {
      ...styles.badgeBase,
      background: "rgba(47, 191, 113, 0.18)",
      border: "1px solid rgba(47, 191, 113, 0.34)",
      color: "#d8ffe6",
    };
  }

  if (s === "RUN") {
    return {
      ...styles.badgeBase,
      background: "rgba(183, 132, 255, 0.16)",
      border: "1px solid rgba(183, 132, 255, 0.34)",
      color: "#efe2ff",
    };
  }

  if (s === "CLOSED") {
    return {
      ...styles.badgeBase,
      background: "rgba(255,255,255,0.06)",
      border: "1px solid rgba(255,255,255,0.12)",
      color: "#eef3fb",
    };
  }

  return {
    ...styles.badgeBase,
    background: "rgba(255,255,255,0.04)",
    border: "1px solid rgba(255,255,255,0.08)",
    color: "#d9e2ef",
  };
}

function resultBadgeStyle(result) {
  const r = String(result || "").toUpperCase().trim();

  if (r === "SL") {
    return {
      ...styles.badgeBase,
      background: "rgba(255, 107, 107, 0.14)",
      border: "1px solid rgba(255, 107, 107, 0.30)",
      color: "#ffd7d7",
    };
  }

  if (r === "TP1" || r === "TP2" || r === "TP1_CLOSE") {
    return {
      ...styles.badgeBase,
      background: "rgba(99, 199, 135, 0.16)",
      border: "1px solid rgba(99, 199, 135, 0.34)",
      color: "#d8ffe6",
    };
  }

  if (r === "RUN_CLOSE" || r === "RUN") {
    return {
      ...styles.badgeBase,
      background: "rgba(183, 132, 255, 0.16)",
      border: "1px solid rgba(183, 132, 255, 0.34)",
      color: "#efe2ff",
    };
  }

  if (r === "BE") {
    return {
      ...styles.badgeBase,
      background: "rgba(255,255,255,0.06)",
      border: "1px solid rgba(255,255,255,0.12)",
      color: "#eef3fb",
    };
  }

  return {
    ...styles.badgeBase,
    background: "rgba(255,255,255,0.04)",
    border: "1px solid rgba(255,255,255,0.08)",
    color: "#d9e2ef",
  };
}

function sideTextStyle() {
  return {
    color: "#eef3fb",
    fontWeight: 800,
  };
}

function buildSymbolStateMap(scanRows, snapshotRows, symbols = []) {
  const order = {
    CLOSED: 0,
    SIN_SETUP: 1,
    SET_UP: 2,
    ENTRY: 3,
    IN_TRADE: 4,
    TP1: 5,
    TP2: 6,
    RUN: 7,
  };

  const out = {};

  symbols.forEach((sym) => {
    out[sym] = { state: "SIN_SETUP", score: 0 };
  });

  const mergedRows = [
    ...(Array.isArray(scanRows) ? scanRows : []),
    ...(Array.isArray(snapshotRows) ? snapshotRows : []),
  ];

  mergedRows.forEach((row) => {
    const sym = row?.symbol;
    const state = normalizeStateKey(row?.state);
    const score = Number(row?.score) || 0;

    if (!sym) return;

    const current = out[sym];
    if (
      !current ||
      (order[state] || 0) > (order[current.state] || 0) ||
      ((order[state] || 0) === (order[current.state] || 0) && score > (current.score || 0))
    ) {
      out[sym] = {
        state,
        score,
      };
    }
  });

  return out;
}

function atlasTrafficLightFromRow(row, analysis, fallbackSymbol = "-") {
  const status = String(analysis?.status || "").toUpperCase();

  if (status === "IMPORT_ERROR" || status === "CRASH") {
    return {
      icon: "🔴",
      text: "ERROR",
      color: "#ff6b6b",
      detail: analysis?.reason || "Error en motor",
    };
  }

  const state = normalizeStateKey(row?.state || analysis?.status);
  const score = Number(row?.score ?? analysis?.score) || 0;
  const tf = row?.tf || "-";
  const sym = row?.symbol || fallbackSymbol;

  const iconByState = {
    RUN: "🟣",
    TP2: "🟢",
    TP1: "🟢",
    IN_TRADE: "🔵",
    ENTRY: "🟠",
    SET_UP: "🟡",
    SIN_SETUP: "⚪",
    CLOSED: "⚪",
  };

  return {
    icon: iconByState[state] || "⚪",
    text: stateLabel(state),
    color: getStateColor(state),
    detail: `${sym} · ${tf} · score ${score}`,
  };
}

function StatusPill({ label, value, active, accent }) {
  return (
    <div
      style={{
        ...styles.statusPill,
        ...(active
          ? {
              background: withAlpha(accent, 0.14),
              border: `1px solid ${withAlpha(accent, 0.30)}`,
            }
          : styles.statusPillOff),
      }}
    >
      <span style={styles.statusLabel}>{label}</span>
      <span style={styles.statusValue}>{value}</span>
    </div>
  );
}

function KpiBox({ label, value }) {
  return (
    <div style={styles.kpiBox}>
      <div style={styles.kpiLabel}>{label}</div>
      <div style={styles.kpiValue}>{value}</div>
    </div>
  );
}

function normalizeItems(value) {
  if (Array.isArray(value)) return value;
  if (Array.isArray(value?.items)) return value.items;
  return [];
}

function extractClosedTrade(item) {
  return {
    ts: item?.ts || "-",
    symbol: item?.symbol || "-",
    tf: item?.tf || "-",
    side: item?.side || "-",
    entry: item?.entry ?? null,
    sl: item?.sl ?? null,
    tp: item?.tp ?? null,
    exit: item?.exit ?? null,
    result: item?.result || "-",
    pips: item?.pips ?? null,
    usd: item?.usd ?? null,
  };
}

function headerChipStyle(color) {
  return {
    display: "inline-flex",
    alignItems: "center",
    gap: 8,
    padding: "7px 12px",
    borderRadius: 999,
    background: "rgba(255,255,255,0.03)",
    border: `1px solid ${withAlpha(color, 0.42)}`,
    color: "#eef3fb",
    fontSize: 12,
    fontWeight: 900,
    whiteSpace: "nowrap",
  };
}

function HeaderChip({ label, color }) {
  return (
    <span style={headerChipStyle(color)}>
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: 999,
          background: color,
          display: "inline-block",
          flexShrink: 0,
        }}
      />
      <span>{label}</span>
    </span>
  );
}

function snapshotSignature(snapshotData) {
  if (!snapshotData || typeof snapshotData !== "object") return "null";

  const candles = Array.isArray(snapshotData.candles) ? snapshotData.candles : [];
  const first = candles[0] || null;
  const last = candles[candles.length - 1] || null;
  const rows = Array.isArray(snapshotData?.ui?.rows) ? snapshotData.ui.rows : [];
  const row = rows[0] || null;

  return [
    snapshotData.world || "",
    snapshotData.symbol || "",
    snapshotData.tf || "",
    snapshotData.atlas_mode || "",
    candles.length,
    first?.t ?? "",
    last?.t ?? "",
    last?.c ?? "",
    row?.state ?? "",
    row?.entry ?? "",
    row?.sl ?? "",
    row?.tp ?? "",
    snapshotData?.analysis?.status ?? "",
    snapshotData?.control?.engine_running ?? "",
    snapshotData?.control?.feed_running ?? "",
  ].join("|");
}

function scanRowsSignature(rows) {
  if (!Array.isArray(rows)) return "[]";
  return rows
    .map((r) =>
      [
        r?.symbol ?? "",
        r?.tf ?? "",
        r?.state ?? "",
        r?.score ?? "",
        r?.entry ?? "",
        r?.sl ?? "",
        r?.tp ?? "",
        r?.tp2 ?? "",
        r?.updated_at ?? "",
      ].join(":")
    )
    .join("||");
}

function summarySignature(summary) {
  if (!summary || typeof summary !== "object") return "null";
  return [
    summary.setups ?? "",
    summary.entries ?? "",
    summary.in_trade ?? "",
    summary.run ?? "",
  ].join("|");
}

function bitClosedSignature(items) {
  if (!Array.isArray(items)) return "[]";
  const last = items[items.length - 1] || {};
  return `${items.length}|${last.ts ?? ""}|${last.symbol ?? ""}|${last.result ?? ""}|${last.usd ?? ""}`;
}

function bitTailSignature(value) {
  if (!value || typeof value !== "object") return "null";
  return JSON.stringify({
    ts: value.ts,
    event: value.event,
    symbol: value?.payload?.symbol,
    state: value?.payload?.state,
    result: value?.payload?.result,
  });
}

function getPollMs(baseVisible, baseHidden) {
  if (typeof document === "undefined") return baseVisible;
  return document.hidden ? baseHidden : baseVisible;
}

export default function App() {
  const [world, setWorld] = useState("ATLAS_IA");
  const [atlasMode, setAtlasMode] = useState("SCALPING_M1");
  const [bitacoraMode, setBitacoraMode] = useState("SCALPING_M1");
  const [symbol, setSymbol] = useState("XAUUSDz");

  const [snapshot, setSnapshot] = useState(null);
  const [scanRows, setScanRows] = useState([]);
  const [scanSummary, setScanSummary] = useState({});
  const [bitClosed, setBitClosed] = useState([]);
  const [bitTail, setBitTail] = useState(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [lastUpdate, setLastUpdate] = useState("");

  const lastSnapshotSigRef = useRef("");
  const lastScanRowsSigRef = useRef("");
  const lastScanSummarySigRef = useRef("");
  const lastBitClosedSigRef = useRef("");
  const lastBitTailSigRef = useRef("");

  const symbols = useMemo(() => SYMBOLS_BY_WORLD[world] || [], [world]);

  const effectiveAtlasMode = useMemo(() => {
    if (world === "PRESESION") return "SCALPING_M5";
    if (world === "GAP") return "SCALPING_M1";
    return atlasMode;
  }, [world, atlasMode]);

  const currentTf = useMemo(() => tfForWorld(world, effectiveAtlasMode), [world, effectiveAtlasMode]);

  const activeAccent = useMemo(() => {
    if (world === "ATLAS_IA") return modeAccent(effectiveAtlasMode);
    return WORLDS.find((w) => w.value === world)?.color || "#ff2fb3";
  }, [world, effectiveAtlasMode]);

  useEffect(() => {
    if (world === "GAP") {
      setSymbol("XAUUSDz");
      return;
    }
    if (symbols.length && !symbols.includes(symbol)) {
      setSymbol(symbols[0]);
    }
  }, [world, symbols, symbol]);

  useEffect(() => {
    if (world === "BITACORA") return;
    setSnapshot(null);
    setScanRows([]);
    setScanSummary({});
    lastSnapshotSigRef.current = "";
    lastScanRowsSigRef.current = "";
    lastScanSummarySigRef.current = "";
  }, [world, effectiveAtlasMode, symbol, currentTf]);

  const analysis = snapshot?.analysis || {};
  const control = snapshot?.control || {};
  const frozenPlans = control?.frozen_plans ?? 0;
  const engineRunning = Boolean(control?.engine_running);
  const feedRunning = Boolean(control?.feed_running);

  const symbolStateMap = useMemo(() => {
  const mergedRows = Array.isArray(scanRows) ? [...scanRows] : [];

  if (activeRow?.symbol) {
    const idx = mergedRows.findIndex((r) => r?.symbol === activeRow.symbol);
    if (idx >= 0) {
      mergedRows[idx] = { ...mergedRows[idx], ...activeRow };
    } else {
      mergedRows.push(activeRow);
    }
  }

  return buildSymbolStateMap(mergedRows, symbols);
}, [scanRows, symbols, activeRow]);

  const selectedScanRow = useMemo(() => {
    return scanRows.find((r) => r?.symbol === symbol) || null;
  }, [scanRows, symbol]);

  const activeRow = useMemo(() => {
    if (selectedScanRow) return selectedScanRow;
    const snapRows = Array.isArray(snapshot?.ui?.rows) ? snapshot.ui.rows : [];
    return snapRows.find((r) => r?.symbol === symbol) || snapRows[0] || null;
  }, [selectedScanRow, snapshot, symbol]);

  const bottomRows = useMemo(() => {
    if (activeRow) return [activeRow];
    const snapRows = Array.isArray(snapshot?.ui?.rows) ? snapshot.ui.rows : [];
    if (snapRows.length) return snapRows;
    return [];
  }, [activeRow, snapshot]);

  const traffic = useMemo(() => {
    return atlasTrafficLightFromRow(activeRow, analysis, symbol);
  }, [activeRow, analysis, symbol]);

  const bitRows = useMemo(() => {
    return normalizeItems(bitClosed).map(extractClosedTrade);
  }, [bitClosed]);

  const bitTotals = useMemo(() => {
    const totalUsd = bitRows.reduce((acc, row) => {
      const v = Number(row?.usd);
      return acc + (Number.isFinite(v) ? v : 0);
    }, 0);

    const totalPips = bitRows.reduce((acc, row) => {
      const v = Number(row?.pips);
      return acc + (Number.isFinite(v) ? v : 0);
    }, 0);

    return {
      totalUsd,
      totalPips,
      count: bitRows.length,
    };
  }, [bitRows]);

  useEffect(() => {
    let cancelled = false;

    let snapshotTimer = null;
    let scanTimer = null;
    let controllerSnapshot = null;
    let controllerScan = null;

    const snapshotInFlightRef = { current: false };
    const scanInFlightRef = { current: false };

    async function tickSnapshot() {
      if (cancelled) return;
      if (world === "BITACORA") return;

      if (snapshotInFlightRef.current) {
        snapshotTimer = setTimeout(tickSnapshot, getPollMs(1800, 4000));
        return;
      }

      snapshotInFlightRef.current = true;
      controllerSnapshot = new AbortController();

      try {
        setError("");

        const snapshotParams = new URLSearchParams({
          world,
          atlas_mode: effectiveAtlasMode,
          symbol: symbol || "",
          tf: currentTf,
          count: "80",
        });

        const snapshotData = await fetchJson(`/api/snapshot?${snapshotParams.toString()}`, {
          signal: controllerSnapshot.signal,
        });

        if (cancelled) return;

        const nextSnapshotSig = snapshotSignature(snapshotData);

        if (lastSnapshotSigRef.current !== nextSnapshotSig) {
          lastSnapshotSigRef.current = nextSnapshotSig;
          setSnapshot(snapshotData);
        }

        setLastUpdate(new Date().toLocaleTimeString());
      } catch (err) {
        if (cancelled) return;
        if (err?.name !== "AbortError") {
          console.error(err);
          setError(err?.message || "Error cargando snapshot");
        }
      } finally {
        snapshotInFlightRef.current = false;
        if (!cancelled) {
          setLoading(false);
          snapshotTimer = setTimeout(tickSnapshot, getPollMs(1800, 4000));
        }
      }
    }

    async function tickScan() {
      if (cancelled) return;

      if (world === "BITACORA") {
        if (scanInFlightRef.current) {
          scanTimer = setTimeout(tickScan, getPollMs(15000, 30000));
          return;
        }

        scanInFlightRef.current = true;
        controllerScan = new AbortController();

        try {
          const [closedRes, tailRes] = await Promise.allSettled([
            fetchJson(`/api/bitacora/closed?mode=${encodeURIComponent(bitacoraMode)}`, {
              signal: controllerScan.signal,
            }),
            fetchJson(`/api/bitacora/tail?mode=${encodeURIComponent(bitacoraMode)}`, {
              signal: controllerScan.signal,
            }),
          ]);

          if (cancelled) return;

          const nextBitClosed = closedRes.status === "fulfilled" ? normalizeItems(closedRes.value) : [];
          const nextBitTail = tailRes.status === "fulfilled" ? tailRes.value : null;

          const nextBitClosedSig = bitClosedSignature(nextBitClosed);
          const nextBitTailSig = bitTailSignature(nextBitTail);

          if (lastBitClosedSigRef.current !== nextBitClosedSig) {
            lastBitClosedSigRef.current = nextBitClosedSig;
            setBitClosed(nextBitClosed);
          }

          if (lastBitTailSigRef.current !== nextBitTailSig) {
            lastBitTailSigRef.current = nextBitTailSig;
            setBitTail(nextBitTail);
          }

          setLastUpdate(new Date().toLocaleTimeString());
        } catch (err) {
          if (cancelled) return;
          if (err?.name !== "AbortError") {
            console.error(err);
            setError(err?.message || "Error cargando bitácora");
          }
        } finally {
          scanInFlightRef.current = false;
          if (!cancelled) {
            setLoading(false);
            scanTimer = setTimeout(tickScan, getPollMs(15000, 30000));
          }
        }

        return;
      }

      if (scanInFlightRef.current) {
        scanTimer = setTimeout(tickScan, getPollMs(20000, 40000));
        return;
      }

      scanInFlightRef.current = true;
      controllerScan = new AbortController();

      try {
        const scanParams = new URLSearchParams({
          world,
          atlas_mode: effectiveAtlasMode,
          count: "40",
        });

        const scanData = await fetchJson(`/api/scan?${scanParams.toString()}`, {
          signal: controllerScan.signal,
        });

        if (cancelled) return;

        const nextRows = Array.isArray(scanData?.rows) ? scanData.rows : [];
        const nextSummary = scanData?.summary || {};

        const nextRowsSig = scanRowsSignature(nextRows);
        const nextSummarySig = summarySignature(nextSummary);

        if (lastScanRowsSigRef.current !== nextRowsSig) {
          lastScanRowsSigRef.current = nextRowsSig;
          setScanRows(nextRows);
        }

        if (lastScanSummarySigRef.current !== nextSummarySig) {
          lastScanSummarySigRef.current = nextSummarySig;
          setScanSummary(nextSummary);
        }
      } catch (err) {
        if (cancelled) return;
        if (err?.name !== "AbortError") {
          console.error(err);
          setError(err?.message || "Error cargando scan");
        }
      } finally {
        scanInFlightRef.current = false;
        if (!cancelled) {
          scanTimer = setTimeout(tickScan, getPollMs(20000, 40000));
        }
      }
    }

  setLoading(true);

Promise.resolve()
  .then(() => tickSnapshot())
  .finally(() => {
    setLoading(false);
  });

const firstScanDelay = world === "BITACORA" ? 6000 : 12000;
scanTimer = setTimeout(tickScan, firstScanDelay);

    return () => {
      cancelled = true;

      if (snapshotTimer) clearTimeout(snapshotTimer);
      if (scanTimer) clearTimeout(scanTimer);

      if (controllerSnapshot) controllerSnapshot.abort();
      if (controllerScan) controllerScan.abort();
    };
  }, [world, effectiveAtlasMode, bitacoraMode, symbol, currentTf]);

  const renderMainTable = () => (
    <div style={styles.tableWrap}>
      <table style={styles.table}>
        <thead>
          <tr>
            <th style={styles.th}>SYMBOL</th>
            <th style={styles.th}>TF</th>
            <th style={styles.th}>SCORE</th>
            <th style={styles.th}>SIDE</th>
            <th style={styles.th}>LOT</th>
            <th style={styles.th}>STATE</th>
            <th style={styles.th}><HeaderChip label="PE" color={activeAccent} /></th>
            <th style={styles.th}><HeaderChip label="TP1" color="#f0b35a" /></th>
            <th style={styles.th}><HeaderChip label="TP2" color="#63c787" /></th>
            <th style={styles.th}><HeaderChip label="SL" color="#ff6b6b" /></th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <tr>
              <td colSpan={10} style={styles.emptyCell}>Cargando...</td>
            </tr>
          ) : bottomRows.length === 0 ? (
            <tr>
              <td colSpan={10} style={styles.emptyCell}>Sin setups visibles.</td>
            </tr>
          ) : (
            bottomRows.map((row, index) => {
              const digits = decimalsBySymbol(row?.symbol);
              const tp1 = row?.parcial ?? row?.partial ?? row?.tp1 ?? row?.tp ?? null;
              const tp2 = row?.tp2 ?? row?.tp ?? null;
              const lot = Number.isFinite(Number(row?.lot)) ? Number(row.lot) : null;

              return (
                <tr key={`${row?.symbol}-${row?.tf}-${index}`} style={styles.tr}>
                  <td style={styles.td}>
                    <button onClick={() => setSymbol(row.symbol)} style={styles.linkBtn}>
                      {row.symbol || "-"}
                    </button>
                  </td>
                  <td style={styles.td}>{row.tf || "-"}</td>
                  <td style={styles.td}>{formatNumber(row.score, 0)}</td>
                  <td style={styles.td}>
                    <span style={sideTextStyle()}>{row?.side || "-"}</span>
                  </td>
                  <td style={styles.td}>{formatNumber(lot, 2)}</td>
                  <td style={styles.td}>
                    <span style={stateBadgeStyle(row?.state)}>{stateLabel(row?.state)}</span>
                  </td>
                  <td style={styles.td}>{formatNumber(row.entry, digits)}</td>
                  <td style={styles.td}>{formatNumber(tp1, digits)}</td>
                  <td style={styles.td}>{formatNumber(tp2, digits)}</td>
                  <td style={styles.td}>{formatNumber(row.sl, digits)}</td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );

  const renderBitacora = () => (
    <div style={styles.bitWrap}>
      <section style={styles.bitTopRow}>
        <div style={styles.segmented}>
          {BITACORA_MODES.map((item) => (
            <button
              key={item.value}
              onClick={() => setBitacoraMode(item.value)}
              style={{
                ...styles.segBtn,
                ...(bitacoraMode === item.value
                  ? {
                      background: withAlpha("#b784ff", 0.18),
                      border: `1px solid ${withAlpha("#b784ff", 0.42)}`,
                      color: "#ffffff",
                    }
                  : null),
              }}
            >
              {item.label}
            </button>
          ))}
        </div>

        <div style={styles.kpiStrip}>
          <KpiBox label="WORLD" value="BITACORA" />
          <KpiBox label="MODE" value={bitacoraMode} />
          <KpiBox label="CERRADOS" value={String(bitTotals.count)} />
          <KpiBox label="PIPS Σ" value={formatSigned(bitTotals.totalPips, 1)} />
          <KpiBox label="USD Σ" value={formatSigned(bitTotals.totalUsd, 2)} />
        </div>
      </section>

      <div style={styles.bitGrid}>
        <div style={styles.cardBitBig}>
          <div style={styles.cardTitle}>TRADES CERRADOS</div>
          <div style={styles.tableWrap}>
            <table style={styles.table}>
              <thead>
                <tr>
                  {["TIME", "SYMBOL", "TF", "SIDE", "RESULT", "PE", "TP2", "EXIT", "SL", "PIPS", "USD"].map((c) => (
                    <th key={c} style={styles.th}>{c}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {!bitRows.length ? (
                  <tr>
                    <td colSpan={11} style={styles.emptyCell}>Sin datos</td>
                  </tr>
                ) : (
                  bitRows.slice(-250).reverse().map((row, i) => {
                    const digits = decimalsBySymbol(row?.symbol);

                    return (
                      <tr key={i} style={styles.tr}>
                        <td style={styles.td}>{row.ts}</td>
                        <td style={styles.td}>{row.symbol}</td>
                        <td style={styles.td}>{row.tf}</td>
                        <td style={styles.td}>{row.side}</td>
                        <td style={styles.td}>
                          <span style={resultBadgeStyle(row.result)}>{row.result}</span>
                        </td>
                        <td style={styles.td}>{formatNumber(row.entry, digits)}</td>
                        <td style={styles.td}>{formatNumber(row.tp, digits)}</td>
                        <td style={styles.td}>{formatNumber(row.exit, digits)}</td>
                        <td style={styles.td}>{formatNumber(row.sl, digits)}</td>
                        <td style={styles.td}>{formatSigned(row.pips, 1)}</td>
                        <td style={styles.td}>{formatSigned(row.usd, 2)}</td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div style={styles.cardBitSide}>
          <div style={styles.cardTitle}>LOG CRUDO</div>
          <pre style={styles.preMajestic}>
            {bitTail ? JSON.stringify(bitTail, null, 2) : "Sin datos"}
          </pre>
        </div>
      </div>
    </div>
  );

  const renderPresesionStrip = () => {
    if (world !== "PRESESION") return null;

    const score = Number(activeRow?.score ?? analysis?.score) || 0;
    const state = stateLabel(activeRow?.state || analysis?.status || "SIN_SETUP");
    const side = activeRow?.side || analysis?.side || "-";
    const note = activeRow?.note || analysis?.reason || "Sin detalle";
    const digits = decimalsBySymbol(symbol);
    const pe = activeRow?.entry ?? null;
    const tp1 = activeRow?.parcial ?? activeRow?.tp1 ?? null;
    const tp2 = activeRow?.tp2 ?? activeRow?.tp ?? null;
    const sl = activeRow?.sl ?? null;

    return (
      <section
        style={{
          ...styles.presesionStrip,
          boxShadow: `0 0 0 1px ${withAlpha(activeAccent, 0.10)}, 0 14px 34px rgba(0,0,0,0.18)`,
        }}
      >
        <div style={styles.presesionStripGrid}>
          <div style={styles.presesionCell}><span style={styles.presesionLabel}>SYMBOL</span><span style={styles.presesionValue}>{symbol}</span></div>
          <div style={styles.presesionCell}><span style={styles.presesionLabel}>TF</span><span style={styles.presesionValue}>{currentTf}</span></div>
          <div style={styles.presesionCell}><span style={styles.presesionLabel}>SCORE</span><span style={styles.presesionValue}>{formatNumber(score, 0)}</span></div>
          <div style={styles.presesionCell}><span style={styles.presesionLabel}>SIDE</span><span style={styles.presesionValue}>{side}</span></div>
          <div style={styles.presesionCell}><span style={styles.presesionLabel}>STATE</span><span style={styles.presesionValue}>{state}</span></div>
          <div style={styles.presesionCell}><span style={styles.presesionLabel}>PE</span><span style={styles.presesionValue}>{formatNumber(pe, digits)}</span></div>
          <div style={styles.presesionCell}><span style={styles.presesionLabel}>TP1</span><span style={styles.presesionValue}>{formatNumber(tp1, digits)}</span></div>
          <div style={styles.presesionCell}><span style={styles.presesionLabel}>TP2</span><span style={styles.presesionValue}>{formatNumber(tp2, digits)}</span></div>
          <div style={styles.presesionCell}><span style={styles.presesionLabel}>SL</span><span style={styles.presesionValue}>{formatNumber(sl, digits)}</span></div>
        </div>
        <div style={styles.presesionNote}>{note}</div>
      </section>
    );
  };

  const hideMainTable = world === "PRESESION";

  return (
    <div style={styles.page}>
      <div style={styles.container}>
        <header
          style={{
            ...styles.hero,
            boxShadow: `0 0 0 1px ${withAlpha(activeAccent, 0.15)}, 0 14px 34px rgba(0,0,0,0.22)`,
          }}
        >
          <div style={styles.heroLeft}>
            <div style={styles.eyebrow}>TEAM ATLAS</div>
            <div style={styles.title}>ATLAS</div>
          </div>

          <div style={styles.statusRow}>
            <div
              style={{
                ...styles.trafficBox,
                border: `1px solid ${withAlpha(traffic.color, 0.35)}`,
                boxShadow: `0 0 0 1px ${withAlpha(traffic.color, 0.10)} inset`,
              }}
            >
              <div style={styles.trafficMain}>
                {traffic.icon} {traffic.text}
              </div>
              <div style={styles.trafficSub}>{traffic.detail}</div>
            </div>

            <StatusPill label="ENGINE" value={engineRunning ? "ON" : "OFF"} active={engineRunning} accent="#63c787" />
            <StatusPill label="FEED" value={feedRunning ? "LIVE" : "PAUSE"} active={feedRunning} accent="#5da8ff" />
            <StatusPill label="FREEZE" value={String(frozenPlans)} active={frozenPlans > 0} accent={activeAccent} />
            <StatusPill label="UPDATE" value={lastUpdate || "-"} active={false} accent={activeAccent} />

            {world !== "BITACORA" && (
              <>
                <StatusPill label="SETUPS" value={String(scanSummary?.setups ?? 0)} active={(scanSummary?.setups ?? 0) > 0} accent="#f0b35a" />
                <StatusPill label="ENTRY" value={String(scanSummary?.entries ?? 0)} active={(scanSummary?.entries ?? 0) > 0} accent="#f28c38" />
              </>
            )}
          </div>
        </header>

        <section
          style={{
            ...styles.controlsSection,
            boxShadow: `0 0 0 1px ${withAlpha(activeAccent, 0.12)}, 0 14px 34px rgba(0,0,0,0.18)`,
          }}
        >
          <div style={styles.compactGrid}>
            <div style={styles.controlBlock}>
              <div style={styles.blockLabel}>WORLD</div>
              <div style={styles.segmented}>
                {WORLDS.map((item) => (
                  <button
                    key={item.value}
                    onClick={() => setWorld(item.value)}
                    style={{
                      ...styles.segBtn,
                      ...(world === item.value
                        ? {
                            background: withAlpha(item.color, 0.22),
                            border: `1px solid ${withAlpha(item.color, 0.48)}`,
                            color: "#ffffff",
                            boxShadow: `0 0 0 1px ${withAlpha(item.color, 0.12)} inset`,
                          }
                        : null),
                    }}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            {world === "ATLAS_IA" && (
              <div style={styles.controlBlock}>
                <div style={styles.blockLabel}>MODO</div>
                <div style={styles.segmented}>
                  {ATLAS_MODES.map((item) => {
                    const localAccent = modeAccent(item.value);
                    return (
                      <button
                        key={item.value}
                        onClick={() => setAtlasMode(item.value)}
                        style={{
                          ...styles.segBtn,
                          ...(effectiveAtlasMode === item.value
                            ? {
                                background: withAlpha(localAccent, 0.22),
                                border: `1px solid ${withAlpha(localAccent, 0.52)}`,
                                color: "#ffffff",
                                boxShadow: `0 0 0 1px ${withAlpha(localAccent, 0.12)} inset`,
                              }
                            : null),
                        }}
                      >
                        {item.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {symbols.length > 0 && (
            <div style={styles.controlBlock}>
              <div style={styles.blockLabel}>SYMBOL</div>
              <div style={styles.symbolGrid}>
                {symbols.map((s) => {
                  const active = s === symbol;
                  const symbolState = normalizeStateKey(symbolStateMap[s]?.state || "SIN_SETUP");
                  const symbolColor = getStateColor(symbolState);

                  return (
                    <button
                      key={s}
                      onClick={() => setSymbol(s)}
                      style={{
                        ...styles.symbolBtn,
                        ...(active
                          ? {
                              background: withAlpha(activeAccent, 0.18),
                              border: `1px solid ${withAlpha(activeAccent, 0.42)}`,
                              color: "#ffffff",
                            }
                          : null),
                      }}
                    >
                      <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                        <span
                          style={{
                            width: 8,
                            height: 8,
                            borderRadius: 999,
                            background: symbolColor,
                            display: "inline-block",
                            flexShrink: 0,
                            boxShadow: `0 0 0 1px ${withAlpha(symbolColor, 0.18)}`,
                          }}
                        />
                        <span>{s}</span>
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {error ? <div style={styles.errorBox}>{error}</div> : null}
        </section>

        {world !== "BITACORA" ? (
          <>
            <section
              style={{
                ...styles.chartSection,
                boxShadow: `0 0 0 1px ${withAlpha(activeAccent, 0.12)}, 0 14px 34px rgba(0,0,0,0.18)`,
              }}
            >
              <div style={styles.chartTopbar}>
                <div>
                  <div style={styles.instrument}>{symbol || "-"}</div>
                  <div style={styles.instrumentMeta}>
                    {world === "ATLAS_IA"
                      ? `${world} - ${effectiveAtlasMode} - ${stateLabel(activeRow?.state || analysis?.status || "SIN_SETUP")} - ${currentTf}`
                      : `${world} - ${stateLabel(activeRow?.state || analysis?.status || "SIN_SETUP")} - ${currentTf}`}
                  </div>
                </div>
              </div>

              <div style={styles.chartFrame}>
                <Charts
  key={`${world}-${effectiveAtlasMode}-${symbol}-${currentTf}`}
  snapshot={snapshot}
  activeRow={activeRow}
  accent={activeAccent}
/>
              </div>
            </section>

            {renderPresesionStrip()}

            {!hideMainTable && (
              <section
                style={{
                  ...styles.card,
                  boxShadow: `0 0 0 1px ${withAlpha(activeAccent, 0.10)}, 0 14px 34px rgba(0,0,0,0.18)`,
                }}
              >
                {renderMainTable()}
              </section>
            )}
          </>
        ) : (
          renderBitacora()
        )}
      </div>
    </div>
  );
}

const styles = {
  page: {
    minHeight: "100vh",
    background: "#070b10",
    color: "#eef3fb",
    fontFamily:
      'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  },
  container: {
    width: "100%",
    maxWidth: "none",
    margin: "0 auto",
    padding: "14px 16px 24px",
    display: "grid",
    gap: 14,
  },
  hero: {
    display: "flex",
    justifyContent: "space-between",
    gap: 14,
    flexWrap: "wrap",
    padding: 12,
    borderRadius: 18,
    border: "1px solid rgba(255,255,255,0.08)",
    background: "linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02))",
  },
  heroLeft: { display: "grid", gap: 2 },
  eyebrow: { fontSize: 10, opacity: 0.65, letterSpacing: 1, fontWeight: 700 },
  title: { fontSize: 18, fontWeight: 900, lineHeight: 1.1 },
  statusRow: { display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-start" },
  statusPill: {
    minWidth: 108,
    borderRadius: 12,
    padding: "8px 10px",
    display: "grid",
    gap: 2,
    border: "1px solid rgba(255,255,255,0.08)",
  },
  statusPillOff: { background: "rgba(255,255,255,0.035)" },
  statusLabel: { fontSize: 10, opacity: 0.72, letterSpacing: 0.55, fontWeight: 700 },
  statusValue: { fontSize: 12, fontWeight: 800 },
  trafficBox: {
    minWidth: 260,
    borderRadius: 14,
    padding: "10px 14px",
    background: "rgba(255,255,255,0.04)",
  },
  trafficMain: { fontSize: 18, fontWeight: 900, lineHeight: 1.1 },
  trafficSub: {
    marginTop: 4,
    fontSize: 12,
    opacity: 0.78,
    maxWidth: 340,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  controlsSection: {
    display: "grid",
    gap: 12,
    padding: 14,
    borderRadius: 18,
    border: "1px solid rgba(255,255,255,0.08)",
    background: "rgba(255,255,255,0.022)",
  },
  compactGrid: { display: "grid", gridTemplateColumns: "1fr", gap: 12 },
  controlBlock: { display: "grid", gap: 8 },
  blockLabel: { fontSize: 11, opacity: 0.68, letterSpacing: 0.8, fontWeight: 800 },
  segmented: { display: "flex", gap: 8, flexWrap: "wrap" },
  segBtn: {
    borderRadius: 11,
    padding: "9px 12px",
    background: "rgba(255,255,255,0.03)",
    border: "1px solid rgba(255,255,255,0.08)",
    color: "#eef3fb",
    fontSize: 12,
    fontWeight: 800,
    cursor: "pointer",
    transition: "all 120ms ease",
  },
  symbolGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(96px, 1fr))",
    gap: 8,
  },
  symbolBtn: {
    borderRadius: 11,
    padding: "9px 10px",
    background: "rgba(255,255,255,0.03)",
    border: "1px solid rgba(255,255,255,0.08)",
    color: "#eef3fb",
    fontSize: 11,
    fontWeight: 800,
    cursor: "pointer",
    transition: "all 120ms ease",
  },
  errorBox: {
    marginTop: 2,
    padding: "10px 12px",
    borderRadius: 12,
    border: "1px solid rgba(255,120,120,0.30)",
    background: "rgba(255,120,120,0.10)",
    color: "#ffc9c9",
    fontSize: 12,
    fontWeight: 700,
  },
  chartSection: {
    display: "grid",
    gap: 10,
    padding: 14,
    borderRadius: 18,
    border: "1px solid rgba(255,255,255,0.08)",
    background: "rgba(255,255,255,0.022)",
  },
  chartTopbar: {
    display: "flex",
    justifyContent: "space-between",
    gap: 12,
    flexWrap: "wrap",
    alignItems: "flex-start",
  },
  instrument: { fontSize: 28, fontWeight: 900, lineHeight: 1 },
  instrumentMeta: { marginTop: 6, fontSize: 14, color: "#d0d9e8", fontWeight: 700 },
  chartFrame: { overflow: "hidden", borderRadius: 16, border: "1px solid rgba(255,255,255,0.08)" },
  card: {
    display: "grid",
    gap: 10,
    padding: 14,
    borderRadius: 18,
    border: "1px solid rgba(255,255,255,0.08)",
    background: "rgba(255,255,255,0.022)",
  },
  presesionStrip: {
    display: "grid",
    gap: 10,
    padding: 14,
    borderRadius: 18,
    border: "1px solid rgba(255,255,255,0.08)",
    background: "rgba(255,255,255,0.022)",
  },
  presesionStripGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(9, minmax(90px, 1fr))",
    gap: 10,
  },
  presesionCell: {
    display: "grid",
    gap: 4,
    padding: "10px 12px",
    borderRadius: 12,
    background: "rgba(255,255,255,0.03)",
    border: "1px solid rgba(255,255,255,0.06)",
  },
  presesionLabel: { fontSize: 10, opacity: 0.65, letterSpacing: 0.65, fontWeight: 800 },
  presesionValue: { fontSize: 13, fontWeight: 800, color: "#eef3fb" },
  presesionNote: {
    fontSize: 12,
    color: "#d0d9e8",
    padding: "2px 2px 0",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  },
  bitWrap: { display: "grid", gap: 16 },
  bitTopRow: {
    display: "flex",
    justifyContent: "space-between",
    gap: 16,
    flexWrap: "wrap",
    alignItems: "center",
  },
  kpiStrip: { display: "flex", gap: 8, flexWrap: "wrap" },
  kpiBox: {
    minWidth: 96,
    borderRadius: 12,
    padding: "8px 10px",
    border: "1px solid rgba(255,255,255,0.08)",
    background: "rgba(255,255,255,0.03)",
  },
  kpiLabel: { fontSize: 10, opacity: 0.65, letterSpacing: 0.65, fontWeight: 800 },
  kpiValue: { marginTop: 4, fontSize: 12, fontWeight: 800 },
  bitGrid: { display: "grid", gridTemplateColumns: "1.35fr 0.85fr", gap: 16 },
  cardBitBig: {
    display: "grid",
    gap: 12,
    padding: 18,
    borderRadius: 20,
    border: "1px solid rgba(183,132,255,0.18)",
    background: "rgba(255,255,255,0.022)",
    boxShadow: "0 0 0 1px rgba(183,132,255,0.08), 0 16px 38px rgba(0,0,0,0.18)",
  },
  cardBitSide: {
    display: "grid",
    gap: 12,
    padding: 18,
    borderRadius: 20,
    border: "1px solid rgba(183,132,255,0.18)",
    background: "rgba(255,255,255,0.022)",
    boxShadow: "0 0 0 1px rgba(183,132,255,0.08), 0 16px 38px rgba(0,0,0,0.18)",
  },
  cardTitle: { fontSize: 16, fontWeight: 900, letterSpacing: 0.4 },
  tableWrap: { width: "100%", overflowX: "auto" },
  table: { width: "100%", minWidth: 1220, borderCollapse: "collapse" },
  th: {
    textAlign: "left",
    padding: "14px 14px",
    fontSize: 14,
    letterSpacing: 0.55,
    opacity: 0.82,
    borderBottom: "1px solid rgba(255,255,255,0.08)",
    fontWeight: 900,
    whiteSpace: "nowrap",
  },
  tr: { borderBottom: "1px solid rgba(255,255,255,0.06)" },
  td: { padding: "16px 14px", fontSize: 16, whiteSpace: "nowrap", color: "#eef3fb" },
  emptyCell: { padding: "22px 14px", fontSize: 16, opacity: 0.8 },
  badgeBase: {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 999,
    padding: "7px 12px",
    fontSize: 13,
    fontWeight: 900,
  },
  linkBtn: {
    border: "none",
    background: "transparent",
    color: "#dce9ff",
    padding: 0,
    cursor: "pointer",
    fontSize: 16,
    fontWeight: 900,
  },
  preMajestic: {
    margin: 0,
    minHeight: 520,
    maxHeight: 820,
    overflow: "auto",
    padding: 14,
    borderRadius: 16,
    background: "#0b1118",
    border: "1px solid rgba(183,132,255,0.16)",
    color: "#e7dcf5",
    fontSize: 12,
    lineHeight: 1.45,
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
    boxShadow: "inset 0 0 0 1px rgba(183,132,255,0.06)",
  },
};