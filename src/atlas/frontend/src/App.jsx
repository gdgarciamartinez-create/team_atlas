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
  { value: "GAP", label: "GAP" },
  { value: "PRESESION", label: "PRESESION" },
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

function minMoveByDigits(digits) {
  if (digits <= 0) return 1;
  return 1 / 10 ** digits;
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

function buildSymbolStateMap(rows = [], symbols = []) {
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

  (Array.isArray(rows) ? rows : []).forEach((row) => {
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
      out[sym] = { state, score };
    }
  });

  return out;
}

function resolveTradeLivePrice(row, analysis) {
  const directCandidates = [
    row?.price,
    row?.last_price,
    row?.current_price,
    analysis?.price,
  ];

  for (const candidate of directCandidates) {
    const n = Number(candidate);
    if (Number.isFinite(n) && n > 0) return n;
  }

  const candles = Array.isArray(row?.candles) ? row.candles : [];
  const last = candles[candles.length - 1];
  const candleClose = Number(last?.c ?? last?.close);
  if (Number.isFinite(candleClose) && candleClose > 0) return candleClose;

  return null;
}

function getTradePositionStatus(row, analysis) {
  const explicit = String(row?.trade_pnl_state || analysis?.trade_pnl_state || "").toUpperCase().trim();
  if (explicit === "POSITIVE") return "POSITIVE";
  if (explicit === "NEGATIVE") return "NEGATIVE";
  if (explicit === "FLAT") return "NEUTRAL";

  const state = normalizeStateKey(row?.state || analysis?.status);
  if (!["ENTRY", "IN_TRADE", "TP1", "TP2", "RUN"].includes(state)) return null;

  const side = String(row?.side || "").toUpperCase().trim();
  const entry = Number(row?.entry);
  const sl = Number(row?.sl);
  const livePrice = resolveTradeLivePrice(row, analysis);

  if (!["BUY", "SELL"].includes(side)) return null;
  if (!Number.isFinite(entry) || !Number.isFinite(livePrice)) return null;

  const tick = minMoveByDigits(decimalsBySymbol(row?.symbol));
  const risk = Number.isFinite(sl) ? Math.abs(entry - sl) : 0;
  const tolerance = risk > 0 ? Math.max(risk * 0.05, tick) : tick * 2;
  const favorableMove = side === "BUY" ? livePrice - entry : entry - livePrice;

  if (favorableMove < -tolerance) return "NEGATIVE";
  if (Math.abs(favorableMove) <= tolerance) return "NEUTRAL";
  return "POSITIVE";
}

function pnlStateColor(state) {
  const s = String(state || "").toUpperCase().trim();
  if (s === "POSITIVE") return "#63c787";
  if (s === "NEGATIVE") return "#ff6b6b";
  return "#9aa6b2";
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

function applyTradePositionToTraffic(baseTraffic, row, analysis) {
  const tradePosition = getTradePositionStatus(row, analysis);

  if (tradePosition === "NEGATIVE") {
    return {
      ...baseTraffic,
      icon: "ðŸ”´",
      color: "#ff6b6b",
      detail: `${baseTraffic.detail} Â· NEG`,
    };
  }

  if (tradePosition === "NEUTRAL") {
    return {
      ...baseTraffic,
      detail: `${baseTraffic.detail} Â· BE`,
    };
  }

  return baseTraffic;
}

function applyTradePositionToTrafficStable(baseTraffic, row, analysis) {
  const tradePosition = getTradePositionStatus(row, analysis);

  if (tradePosition === "NEGATIVE") {
    return {
      ...baseTraffic,
      icon: "\uD83D\uDD34",
      color: "#ff6b6b",
      detail: `${baseTraffic.detail} - NEG`,
    };
  }

  if (tradePosition === "NEUTRAL") {
    return {
      ...baseTraffic,
      detail: `${baseTraffic.detail} - BE`,
    };
  }

  return baseTraffic;
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
    world: item?.world || "-",
    atlas_mode: item?.atlas_mode || "-",
    trade_id: item?.trade_id || "-",
    leg_id: item?.leg_id ?? null,
    partial_percent: item?.partial_percent ?? null,
    symbol: item?.symbol || "-",
    tf: item?.tf || "-",
    score: item?.score ?? null,
    side: item?.side || "-",
    lot: item?.lot ?? null,
    lot_raw: item?.lot_raw ?? null,
    lot_capped: item?.lot_capped ?? null,
    lot_cap_reason: item?.lot_cap_reason ?? null,
    entry: item?.entry ?? null,
    sl: item?.sl ?? null,
    tp: item?.tp ?? null,
    exit: item?.close_price ?? item?.exit ?? null,
    result: item?.result || "-",
    pips: item?.pips ?? null,
    usd: item?.usd ?? null,
  };
}

function extractTradeSummary(item) {
  return {
    trade_id: item?.trade_id || "-",
    world: item?.world || "-",
    atlas_mode: item?.atlas_mode || item?.mode || "-",
    symbol: item?.symbol || "-",
    tf: item?.tf || "-",
    side: item?.side || "-",
    lot_total: item?.lot_total ?? null,
    risk_percent: item?.risk_percent ?? null,
    pnl_total_usd: item?.pnl_total_usd ?? null,
    pnl_total_points: item?.pnl_total_points ?? null,
    legs_count: item?.legs_count ?? null,
    exit_final_reason: item?.exit_final_reason || "-",
    score_max: item?.score_max ?? null,
    score_avg: item?.score_avg ?? null,
    had_partial: item?.had_partial ?? null,
    had_be_close: item?.had_be_close ?? null,
    had_tp2: item?.had_tp2 ?? null,
    opened_at: item?.opened_at || "-",
    closed_at: item?.closed_at || "-",
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
    row?.tp1 ?? "",
    row?.tp1_price ?? "",
    row?.floating_usd ?? "",
    row?.trade_pnl_state ?? "",
    snapshotData?.analysis?.status ?? "",
    snapshotData?.analysis?.floating_usd ?? "",
    snapshotData?.analysis?.trade_pnl_state ?? "",
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
        r?.tp1 ?? "",
        r?.tp1_price ?? "",
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
    summary.live ?? "",
  ].join("|");
}

function bitClosedSignature(items) {
  if (!Array.isArray(items)) return "[]";
  const last = items[items.length - 1] || {};
  return `${items.length}|${last.ts ?? ""}|${last.symbol ?? ""}|${last.result ?? ""}|${last.usd ?? ""}|${last.score ?? ""}`;
}

function bitSummarySignature(items) {
  if (!Array.isArray(items)) return "[]";
  const last = items[items.length - 1] || {};
  return `${items.length}|${last.trade_id ?? ""}|${last.symbol ?? ""}|${last.pnl_total_usd ?? ""}|${last.legs_count ?? ""}|${last.exit_final_reason ?? ""}`;
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
  const [bitSummary, setBitSummary] = useState([]);
  const [bitTail, setBitTail] = useState(null);
  const [bitMetrics, setBitMetrics] = useState({});
  const [bitSummaryMetrics, setBitSummaryMetrics] = useState({});
  const [bitacoraSymbol, setBitacoraSymbol] = useState("");
  const [bitacoraFromTs, setBitacoraFromTs] = useState("");
  const [bitacoraToTs, setBitacoraToTs] = useState("");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [lastUpdate, setLastUpdate] = useState("");

  const lastSnapshotSigRef = useRef("");
  const lastScanRowsSigRef = useRef("");
  const lastScanSummarySigRef = useRef("");
  const lastBitClosedSigRef = useRef("");
  const lastBitSummarySigRef = useRef("");
  const lastBitTailSigRef = useRef("");
  const lastSymbolStateRef = useRef({});

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

const selectedScanRow = useMemo(() => {
  return scanRows.find((r) => r?.symbol === symbol) || null;
}, [scanRows, symbol]);

const snapshotActiveRow = useMemo(() => {
  const snapRows = Array.isArray(snapshot?.ui?.rows) ? snapshot.ui.rows : [];
  return snapRows.find((r) => r?.symbol === symbol) || snapRows[0] || null;
}, [snapshot, symbol]);

const snapshotHasFrozenPlan = useMemo(() => {
  const s = String(snapshotActiveRow?.state || "").toUpperCase().trim();
  return ["SET_UP", "ENTRY", "IN_TRADE", "TP1", "TP2", "RUN"].includes(s);
}, [snapshotActiveRow]);

const activeRow = useMemo(() => {
  if (snapshotHasFrozenPlan) return snapshotActiveRow;
  if (selectedScanRow) return selectedScanRow;
  return snapshotActiveRow;
}, [snapshotHasFrozenPlan, snapshotActiveRow, selectedScanRow]);

  const bottomRows = useMemo(() => {
    if (activeRow) return [activeRow];
    const snapRows = Array.isArray(snapshot?.ui?.rows) ? snapshot.ui.rows : [];
    if (snapRows.length) return snapRows;
    return [];
  }, [activeRow, snapshot]);

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

    const freshMap = buildSymbolStateMap(mergedRows, symbols);

    const hasAnyUsefulData =
      Array.isArray(scanRows) && scanRows.length > 0;

    if (hasAnyUsefulData) {
      lastSymbolStateRef.current = freshMap;
      return freshMap;
    }

    return Object.keys(lastSymbolStateRef.current || {}).length
      ? lastSymbolStateRef.current
      : freshMap;
  }, [scanRows, symbols, activeRow]);

  const traffic = useMemo(() => {
    return applyTradePositionToTrafficStable(
      atlasTrafficLightFromRow(activeRow, analysis, symbol),
      activeRow,
      analysis
    );
  }, [activeRow, analysis, symbol]);

  const activeTradePnlState = String(
    activeRow?.trade_pnl_state || analysis?.trade_pnl_state || "FLAT"
  ).toUpperCase();
  const activeFloatingUsd =
    Number.isFinite(Number(activeRow?.floating_usd))
      ? Number(activeRow?.floating_usd)
      : Number.isFinite(Number(analysis?.floating_usd))
        ? Number(analysis?.floating_usd)
        : null;
  const activeFloatingMove =
    Number.isFinite(Number(activeRow?.floating_point_move))
      ? Number(activeRow?.floating_point_move)
      : Number.isFinite(Number(analysis?.floating_point_move))
        ? Number(analysis?.floating_point_move)
        : Number.isFinite(Number(activeRow?.floating_pip_move))
          ? Number(activeRow?.floating_pip_move)
          : Number.isFinite(Number(analysis?.floating_pip_move))
            ? Number(analysis?.floating_pip_move)
            : Number.isFinite(Number(activeRow?.floating_price_move))
              ? Number(activeRow?.floating_price_move)
              : Number.isFinite(Number(analysis?.floating_price_move))
                ? Number(analysis?.floating_price_move)
                : null;

  const bitRows = useMemo(() => {
    return normalizeItems(bitClosed).map(extractClosedTrade);
  }, [bitClosed]);

  const bitSummaryRows = useMemo(() => {
    return normalizeItems(bitSummary).map(extractTradeSummary);
  }, [bitSummary]);

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

  const bitacoraQuery = useMemo(() => {
    const params = new URLSearchParams();
    params.set("mode", bitacoraMode);
    if (bitacoraSymbol.trim()) params.set("symbol", bitacoraSymbol.trim());
    if (bitacoraFromTs) params.set("from_ts", new Date(bitacoraFromTs).toISOString());
    if (bitacoraToTs) params.set("to_ts", new Date(bitacoraToTs).toISOString());
    return params.toString();
  }, [bitacoraMode, bitacoraSymbol, bitacoraFromTs, bitacoraToTs]);

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
        snapshotTimer = setTimeout(tickSnapshot, getPollMs(1700, 3500));
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
          snapshotTimer = setTimeout(tickSnapshot, getPollMs(1700, 3500));
        }
      }
    }

    async function tickScan() {
      if (cancelled) return;

      if (world === "BITACORA") {
        if (scanInFlightRef.current) {
          scanTimer = setTimeout(tickScan, getPollMs(12000, 24000));
          return;
        }

        scanInFlightRef.current = true;
        controllerScan = new AbortController();

        try {
          const [closedRes, summaryRes, tailRes] = await Promise.allSettled([
            fetchJson(`/api/bitacora/closed?${bitacoraQuery}`, {
              signal: controllerScan.signal,
            }),
            fetchJson(`/api/bitacora/summary?${bitacoraQuery}`, {
              signal: controllerScan.signal,
            }),
            fetchJson(`/api/bitacora/tail?${bitacoraQuery}`, {
              signal: controllerScan.signal,
            }),
          ]);

          if (cancelled) return;

          const nextBitClosed = closedRes.status === "fulfilled" ? normalizeItems(closedRes.value) : [];
          const nextBitSummary = summaryRes.status === "fulfilled" ? normalizeItems(summaryRes.value) : [];
          const nextBitTail = tailRes.status === "fulfilled" ? tailRes.value : null;
          const nextBitMetrics =
            closedRes.status === "fulfilled" ? closedRes.value?.metrics_summary || {} : {};
          const nextBitSummaryMetrics =
            summaryRes.status === "fulfilled" ? summaryRes.value?.metrics_summary || {} : {};

          const nextBitClosedSig = bitClosedSignature(nextBitClosed);
          const nextBitSummarySig = bitSummarySignature(nextBitSummary);
          const nextBitTailSig = bitTailSignature(nextBitTail);

          if (lastBitClosedSigRef.current !== nextBitClosedSig) {
            lastBitClosedSigRef.current = nextBitClosedSig;
            setBitClosed(nextBitClosed);
          }

          if (lastBitSummarySigRef.current !== nextBitSummarySig) {
            lastBitSummarySigRef.current = nextBitSummarySig;
            setBitSummary(nextBitSummary);
          }

          if (lastBitTailSigRef.current !== nextBitTailSig) {
            lastBitTailSigRef.current = nextBitTailSig;
            setBitTail(nextBitTail);
          }

          setBitMetrics(nextBitMetrics);
          setBitSummaryMetrics(nextBitSummaryMetrics);

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
            scanTimer = setTimeout(tickScan, getPollMs(12000, 24000));
          }
        }

        return;
      }

      if (scanInFlightRef.current) {
        scanTimer = setTimeout(tickScan, getPollMs(5000, 9000));
        return;
      }

      scanInFlightRef.current = true;
      controllerScan = new AbortController();

      try {
        const scanParams = new URLSearchParams({
          world,
          atlas_mode: effectiveAtlasMode,
          count: "80",
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
          scanTimer = setTimeout(tickScan, getPollMs(5000, 9000));
        }
      }
    }

    setLoading(true);
    tickSnapshot();

    const firstScanDelay = world === "BITACORA" ? 2500 : 2500;
    scanTimer = setTimeout(tickScan, firstScanDelay);

    return () => {
      cancelled = true;

      if (snapshotTimer) clearTimeout(snapshotTimer);
      if (scanTimer) clearTimeout(scanTimer);

      if (controllerSnapshot) controllerSnapshot.abort();
      if (controllerScan) controllerScan.abort();
    };
  }, [world, effectiveAtlasMode, bitacoraMode, bitacoraQuery, symbol, currentTf]);

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

              const tp1 =
                row?.parcial ??
                row?.partial ??
                row?.tp1 ??
                row?.tp1_price ??
                row?.tp_first ??
                row?.tp_1 ??
                row?.first_tp ??
                row?.tp ??
                null;

              const tp2 =
                row?.tp2 ??
                row?.tp_second ??
                row?.tp_2 ??
                row?.second_tp ??
                row?.tp ??
                null;

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
          <KpiBox label="TRADES" value={String(bitSummaryMetrics?.total_trades ?? bitMetrics?.total_trades ?? bitTotals.count)} />
          <KpiBox label="WIN RATE" value={`${formatNumber(bitSummaryMetrics?.win_rate ?? bitMetrics?.win_rate, 2)}%`} />
          <a
            href={`/api/bitacora/export?${bitacoraQuery}`}
            style={{
              ...styles.segBtn,
              textDecoration: "none",
              display: "inline-flex",
              alignItems: "center",
            }}
          >
            LEGS CSV
          </a>
          <a
            href={`/api/bitacora/export?${bitacoraQuery}&format=json`}
            style={{
              ...styles.segBtn,
              textDecoration: "none",
              display: "inline-flex",
              alignItems: "center",
            }}
          >
            LEGS JSON
          </a>
          <a
            href={`/api/bitacora/summary/export?${bitacoraQuery}`}
            style={{
              ...styles.segBtn,
              textDecoration: "none",
              display: "inline-flex",
              alignItems: "center",
            }}
          >
            SUMMARY CSV
          </a>
          <a
            href={`/api/bitacora/summary/export?${bitacoraQuery}&format=json`}
            style={{
              ...styles.segBtn,
              textDecoration: "none",
              display: "inline-flex",
              alignItems: "center",
            }}
          >
            SUMMARY JSON
          </a>
          <KpiBox label="PIPS Σ" value={formatSigned(bitTotals.totalPips, 1)} />
          <KpiBox label="USD Σ" value={formatSigned(bitMetrics?.total_pnl_usd ?? bitTotals.totalUsd, 2)} />
        </div>
      </section>

      <section style={styles.bitFilterRow}>
        <input
          value={bitacoraSymbol}
          onChange={(e) => setBitacoraSymbol(e.target.value.toUpperCase())}
          placeholder="SYMBOL"
          style={styles.bitInput}
        />
        <input
          type="datetime-local"
          value={bitacoraFromTs}
          onChange={(e) => setBitacoraFromTs(e.target.value)}
          style={styles.bitInput}
        />
        <input
          type="datetime-local"
          value={bitacoraToTs}
          onChange={(e) => setBitacoraToTs(e.target.value)}
          style={styles.bitInput}
        />
        <button
          onClick={() => {
            setBitacoraSymbol("");
            setBitacoraFromTs("");
            setBitacoraToTs("");
          }}
          style={styles.segBtn}
        >
          LIMPIAR FILTROS
        </button>
      </section>

      <div style={styles.bitGrid}>
        <div style={styles.cardBitBig}>
          <div style={styles.cardTitle}>TRADES CERRADOS</div>
          <div style={styles.tableWrap}>
            <table style={styles.table}>
              <thead>
                <tr>
                  {["TIME", "WORLD", "MODE", "TRADE", "LEG", "PARTIAL %", "SYMBOL", "TF", "SCORE", "SIDE", "LOT", "RESULT", "PE", "TP2", "EXIT", "SL", "PIPS", "USD"].map((c) => (
                    <th key={c} style={styles.th}>{c}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {!bitRows.length ? (
                  <tr>
                    <td colSpan={18} style={styles.emptyCell}>Sin datos</td>
                  </tr>
                ) : (
                  bitRows.slice(-250).reverse().map((row, i) => {
                    const digits = decimalsBySymbol(row?.symbol);

                    return (
                      <tr key={i} style={styles.tr}>
                        <td style={styles.td}>{row.ts}</td>
                        <td style={styles.td}>{row.world}</td>
                        <td style={styles.td}>{row.atlas_mode}</td>
                        <td style={styles.td}>{row.trade_id}</td>
                        <td style={styles.td}>{formatNumber(row.leg_id, 0)}</td>
                        <td style={styles.td}>{formatNumber(row.partial_percent, 0)}</td>
                        <td style={styles.td}>{row.symbol}</td>
                        <td style={styles.td}>{row.tf}</td>
                        <td style={styles.td}>{formatNumber(row.score, 0)}</td>
                        <td style={styles.td}>{row.side}</td>
                        <td style={styles.td}>{formatNumber(row.lot, 2)}</td>
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
          <div style={styles.cardTitle}>METRICS SUMMARY</div>
          <div style={styles.metricList}>
            <div style={styles.metricRow}><span>Total trades</span><strong>{bitSummaryMetrics?.total_trades ?? 0}</strong></div>
            <div style={styles.metricRow}><span>Win / Loss / Flat</span><strong>{`${bitSummaryMetrics?.win_trades ?? 0} / ${bitSummaryMetrics?.loss_trades ?? 0} / ${bitSummaryMetrics?.flat_trades ?? 0}`}</strong></div>
            <div style={styles.metricRow}><span>Avg trade USD</span><strong>{formatSigned(bitSummaryMetrics?.avg_trade_usd, 2)}</strong></div>
            <div style={styles.metricRow}><span>Avg win / loss</span><strong>{`${formatSigned(bitSummaryMetrics?.avg_win_usd, 2)} / ${formatSigned(bitSummaryMetrics?.avg_loss_usd, 2)}`}</strong></div>
            <div style={styles.metricRow}><span>Max win / loss</span><strong>{`${formatSigned(bitSummaryMetrics?.max_win_usd, 2)} / ${formatSigned(bitSummaryMetrics?.max_loss_usd, 2)}`}</strong></div>
            <div style={styles.metricRow}><span>Partials / TP2 / SL</span><strong>{`${bitSummaryMetrics?.total_partials ?? 0} / ${bitSummaryMetrics?.total_tp2_final ?? 0} / ${bitSummaryMetrics?.total_sl ?? 0}`}</strong></div>
            <div style={styles.metricRow}><span>BE / Manual</span><strong>{`${bitSummaryMetrics?.total_be_close ?? 0} / ${bitSummaryMetrics?.total_manual_close ?? 0}`}</strong></div>
            <div style={styles.metricRow}><span>Symbols</span><strong>{bitSummaryMetrics?.symbols_count ?? 0}</strong></div>
            <div style={styles.metricRow}><span>Best symbol</span><strong>{bitSummaryMetrics?.best_symbol_by_usd?.symbol ? `${bitSummaryMetrics.best_symbol_by_usd.symbol} ${formatSigned(bitSummaryMetrics.best_symbol_by_usd.usd, 2)}` : "-"}</strong></div>
            <div style={styles.metricRow}><span>Worst symbol</span><strong>{bitSummaryMetrics?.worst_symbol_by_usd?.symbol ? `${bitSummaryMetrics.worst_symbol_by_usd.symbol} ${formatSigned(bitSummaryMetrics.worst_symbol_by_usd.usd, 2)}` : "-"}</strong></div>
          </div>

          <div style={styles.cardTitle}>LOG CRUDO</div>
          <pre style={styles.preMajestic}>
            {bitTail ? JSON.stringify(bitTail, null, 2) : "Sin datos"}
          </pre>
        </div>
      </div>

      <div style={styles.cardBitBig}>
        <div style={styles.cardTitle}>TRADE SUMMARY</div>
        <div style={styles.tableWrap}>
          <table style={styles.table}>
            <thead>
              <tr>
                {["TRADE ID", "WORLD", "MODE", "SYMBOL", "TF", "SIDE", "LOT", "RISK %", "USD", "POINTS", "LEGS", "EXIT", "SCORE MAX", "SCORE AVG", "PARTIAL", "BE", "TP2", "OPENED", "CLOSED"].map((c) => (
                  <th key={c} style={styles.th}>{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {!bitSummaryRows.length ? (
                <tr>
                  <td colSpan={19} style={styles.emptyCell}>Sin datos</td>
                </tr>
              ) : (
                bitSummaryRows.slice(-250).reverse().map((row, i) => (
                  <tr key={`${row.trade_id}-${i}`} style={styles.tr}>
                    <td style={styles.td}>{row.trade_id}</td>
                    <td style={styles.td}>{row.world}</td>
                    <td style={styles.td}>{row.atlas_mode}</td>
                    <td style={styles.td}>{row.symbol}</td>
                    <td style={styles.td}>{row.tf}</td>
                    <td style={styles.td}>{row.side}</td>
                    <td style={styles.td}>{formatNumber(row.lot_total, 2)}</td>
                    <td style={styles.td}>{formatNumber(row.risk_percent, 2)}</td>
                    <td style={styles.td}>{formatSigned(row.pnl_total_usd, 2)}</td>
                    <td style={styles.td}>{formatSigned(row.pnl_total_points, 2)}</td>
                    <td style={styles.td}>{formatNumber(row.legs_count, 0)}</td>
                    <td style={styles.td}>
                      <span style={resultBadgeStyle(row.exit_final_reason)}>{row.exit_final_reason}</span>
                    </td>
                    <td style={styles.td}>{formatNumber(row.score_max, 2)}</td>
                    <td style={styles.td}>{formatNumber(row.score_avg, 2)}</td>
                    <td style={styles.td}>{row.had_partial ? "YES" : "NO"}</td>
                    <td style={styles.td}>{row.had_be_close ? "YES" : "NO"}</td>
                    <td style={styles.td}>{row.had_tp2 ? "YES" : "NO"}</td>
                    <td style={styles.td}>{row.opened_at}</td>
                    <td style={styles.td}>{row.closed_at}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
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
    const tp1 =
      activeRow?.parcial ??
      activeRow?.tp1 ??
      activeRow?.tp1_price ??
      activeRow?.tp ??
      null;
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
            <StatusPill
              label="TRADE"
              value={activeFloatingUsd === null ? activeTradePnlState : formatSigned(activeFloatingUsd, 2)}
              active={activeFloatingUsd !== null || activeTradePnlState !== "FLAT"}
              accent={pnlStateColor(activeTradePnlState)}
            />
            <StatusPill
              label="MOVE"
              value={activeFloatingMove === null ? "-" : formatSigned(activeFloatingMove, 2)}
              active={activeFloatingMove !== null}
              accent={pnlStateColor(activeTradePnlState)}
            />
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
                  <div style={{ ...styles.instrumentMeta, display: "inline-flex", alignItems: "center", gap: 10 }}>
                    <span
                      style={{
                        width: 11,
                        height: 11,
                        borderRadius: 999,
                        background: pnlStateColor(activeTradePnlState),
                        display: "inline-block",
                        boxShadow: `0 0 0 1px ${withAlpha(pnlStateColor(activeTradePnlState), 0.28)}`,
                      }}
                    />
                    <span>
                      {world === "ATLAS_IA"
                        ? `${world} - ${effectiveAtlasMode} - ${stateLabel(activeRow?.state || analysis?.status || "SIN_SETUP")} - ${currentTf}`
                        : `${world} - ${stateLabel(activeRow?.state || analysis?.status || "SIN_SETUP")} - ${currentTf}`}
                    </span>
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
  bitFilterRow: {
    display: "flex",
    gap: 10,
    flexWrap: "wrap",
    alignItems: "center",
  },
  kpiStrip: { display: "flex", gap: 8, flexWrap: "wrap" },
  bitInput: {
    minWidth: 160,
    borderRadius: 12,
    padding: "10px 12px",
    border: "1px solid rgba(255,255,255,0.10)",
    background: "rgba(255,255,255,0.03)",
    color: "#eef3fb",
    fontSize: 13,
    outline: "none",
  },
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
  metricList: { display: "grid", gap: 8 },
  metricRow: {
    display: "flex",
    justifyContent: "space-between",
    gap: 12,
    padding: "8px 10px",
    borderRadius: 12,
    background: "rgba(255,255,255,0.03)",
    border: "1px solid rgba(255,255,255,0.06)",
    fontSize: 13,
  },
  tableWrap: { width: "100%", overflowX: "auto" },
  table: { width: "100%", minWidth: 1320, borderCollapse: "collapse" },
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
