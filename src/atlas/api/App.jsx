import { useEffect, useMemo, useState } from "react";
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

function pipFactorBySymbol(sym) {
  if (!sym) return 10000;
  if (sym.startsWith("XAU")) return 10;
  if (sym.startsWith("BTC")) return 1;
  if (sym.startsWith("USTEC")) return 1;
  if (sym.startsWith("USOIL")) return 100;
  if (sym.includes("JPY")) return 100;
  return 10000;
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
    return "H1";
  }
  return "-";
}

async function fetchJson(url, options) {
  const res = await fetch(url, options);
  if (!res.ok) {
    const err = new Error(`HTTP ${res.status}`);
    err.status = res.status;
    throw err;
  }
  return res.json();
}function normalizeStateKey(state) {
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

function sideBadgeStyle(side) {
  const s = String(side || "").toUpperCase();

  if (s === "BUY") {
    return {
      ...styles.badgeBase,
      background: "rgba(99, 199, 135, 0.16)",
      border: "1px solid rgba(99, 199, 135, 0.34)",
      color: "#d8ffe6",
    };
  }

  if (s === "SELL") {
    return {
      ...styles.badgeBase,
      background: "rgba(240, 179, 90, 0.16)",
      border: "1px solid rgba(240, 179, 90, 0.34)",
      color: "#ffe6bf",
    };
  }

  return {
    ...styles.badgeBase,
    background: "rgba(255,255,255,0.04)",
    border: "1px solid rgba(255,255,255,0.08)",
    color: "#d9e2ef",
  };
}

function usdBadgeStyle(v) {
  const n = Number(v);
  if (!Number.isFinite(n)) {
    return {
      ...styles.badgeBase,
      background: "rgba(255,255,255,0.04)",
      border: "1px solid rgba(255,255,255,0.08)",
      color: "#d9e2ef",
    };
  }

  if (n > 0) {
    return {
      ...styles.badgeBase,
      background: "rgba(99, 199, 135, 0.16)",
      border: "1px solid rgba(99, 199, 135, 0.34)",
      color: "#d8ffe6",
    };
  }

  if (n < 0) {
    return {
      ...styles.badgeBase,
      background: "rgba(255, 107, 107, 0.14)",
      border: "1px solid rgba(255, 107, 107, 0.30)",
      color: "#ffd7d7",
    };
  }

  return {
    ...styles.badgeBase,
    background: "rgba(255,255,255,0.04)",
    border: "1px solid rgba(255,255,255,0.08)",
    color: "#d9e2ef",
  };
}function buildSymbolStateMap(rows, symbols = []) {
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

  (rows || []).forEach((row) => {
    const sym = row?.symbol;
    const state = normalizeStateKey(row?.state);

    if (!sym) return;

    const current = out[sym];
    if (!current || (order[state] || 0) > (order[current.state] || 0)) {
      out[sym] = {
        state,
        score: Number(row?.score) || 0,
      };
    }
  });

  return out;
}

function atlasTrafficLight(rows, analysis, accent) {
  const status = String(analysis?.status || "").toUpperCase();

  if (status === "IMPORT_ERROR" || status === "CRASH") {
    return {
      icon: "🔴",
      text: "ERROR",
      color: "#ff6b6b",
      detail: analysis?.reason || "Error en motor",
    };
  }

  if (!rows || rows.length === 0) {
    return {
      icon: "🟡",
      text: "SIN SETUP",
      color: "#f0b35a",
      detail: "Sin setups 9+",
    };
  }

  const sorted = [...rows].sort((a, b) => (Number(b?.score) || 0) - (Number(a?.score) || 0));

  const run = sorted.find((r) => normalizeStateKey(r?.state) === "RUN");
  if (run) {
    return {
      icon: "🟣",
      text: stateLabel(run.state),
      color: getStateColor(run.state),
      detail: `${run.symbol} · ${run.tf} · score ${run.score ?? "-"}`,
    };
  }

  const tp2 = sorted.find((r) => normalizeStateKey(r?.state) === "TP2");
  if (tp2) {
    return {
      icon: "🟢",
      text: stateLabel(tp2.state),
      color: getStateColor(tp2.state),
      detail: `${tp2.symbol} · ${tp2.tf} · score ${tp2.score ?? "-"}`,
    };
  }

  const tp1 = sorted.find((r) => normalizeStateKey(r?.state) === "TP1");
  if (tp1) {
    return {
      icon: "🟢",
      text: stateLabel(tp1.state),
      color: getStateColor(tp1.state),
      detail: `${tp1.symbol} · ${tp1.tf} · score ${tp1.score ?? "-"}`,
    };
  }

  const inTrade = sorted.find((r) => normalizeStateKey(r?.state) === "IN_TRADE");
  if (inTrade) {
    return {
      icon: "🔵",
      text: stateLabel(inTrade.state),
      color: getStateColor(inTrade.state),
      detail: `${inTrade.symbol} · ${inTrade.tf} · score ${inTrade.score ?? "-"}`,
    };
  }

  const entry = sorted.find((r) => normalizeStateKey(r?.state) === "ENTRY");
  if (entry) {
    return {
      icon: "🟠",
      text: stateLabel(entry.state),
      color: getStateColor(entry.state),
      detail: `${entry.symbol} · ${entry.tf} · score ${entry.score ?? "-"}`,
    };
  }

  const setup = sorted.find((r) => normalizeStateKey(r?.state) === "SET_UP");
  if (setup) {
    return {
      icon: "🟡",
      text: stateLabel(setup.state),
      color: getStateColor(setup.state),
      detail: `${setup.symbol} · ${setup.tf} · score ${setup.score ?? "-"}`,
    };
  }

  const best = sorted[0];
  return {
    icon: "⚪",
    text: "SIN SETUP",
    color: "#6b7280",
    detail: best?.symbol ? `${best.symbol} · ${best.tf} · score ${best.score ?? "-"}` : "Sin setups",
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

function normalizeBitOps(value) {
  if (Array.isArray(value)) return value;
  if (Array.isArray(value?.ops)) return value.ops;
  if (Array.isArray(value?.items)) return value.items;
  return [];
}function extractBitItem(item) {
  const payload = item?.payload || item || {};

  return {
    ts: item?.ts || item?.time || payload?.ts || "-",
    event: item?.event || payload?.event || "-",
    symbol: payload?.symbol || item?.symbol || "-",
    tf: payload?.tf || item?.tf || "-",
    side: payload?.side || item?.side || "-",
    state: payload?.to_state || item?.state || payload?.state || "-",
    entry: payload?.entry ?? item?.entry ?? null,
    sl: payload?.sl ?? item?.sl ?? null,
    tp: payload?.tp ?? item?.tp ?? null,
    parcial:
      payload?.parcial ??
      payload?.partial ??
      payload?.tp1 ??
      item?.parcial ??
      item?.partial ??
      item?.tp1 ??
      null,
    pips: payload?.pips ?? item?.pips ?? null,
    usd: payload?.usd ?? payload?.pnl_usd ?? payload?.pnl ?? item?.usd ?? item?.pnl_usd ?? item?.pnl ?? null,
  };
}

function computeDerivedPips(row) {
  if (row?.pips !== null && row?.pips !== undefined && Number.isFinite(Number(row.pips))) {
    return Number(row.pips);
  }

  const entry = Number(row?.entry);
  const parcial = Number(row?.parcial);
  const tp = Number(row?.tp);
  const side = String(row?.side || "").toUpperCase();
  const sym = row?.symbol;
  const factor = pipFactorBySymbol(sym);

  if (!Number.isFinite(entry)) return null;

  const target = Number.isFinite(parcial) ? parcial : tp;
  if (!Number.isFinite(target)) return null;

  if (side === "BUY") return (target - entry) * factor;
  if (side === "SELL") return (entry - target) * factor;
  return null;
}

function computeDerivedUsd(row) {
  if (row?.usd !== null && row?.usd !== undefined && Number.isFinite(Number(row.usd))) {
    return Number(row.usd);
  }
  return null;
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

function buildAnalysisSummary({ row, analysis, atlasMode, currentTf, world }) {
  const side = row?.side || analysis?.side || "-";
  const score = row?.score ?? analysis?.score ?? "-";
  const status = stateLabel(row?.state || analysis?.status || "SIN_SETUP");
  const note = row?.note || analysis?.reason || "sin detalle fino";
  const symbol = row?.symbol || analysis?.symbol || "-";

  const texto = `${symbol} en ${currentTf} está en ${status}. Lado dominante: ${
    side !== "-" ? side : "neutral"
  }. Score actual ${score}. Nota activa: ${note}.`;

  return {
    titulo: `${world === "ATLAS_IA" ? atlasMode : world} · ${currentTf} · ${status}`,
    texto,
  };
}

export default function App() {
  const [world, setWorld] = useState("ATLAS_IA");
  const [atlasMode, setAtlasMode] = useState("SCALPING_M1");
  const [bitacoraMode, setBitacoraMode] = useState("SCALPING_M1");
  const [symbol, setSymbol] = useState("XAUUSDz");

  const [snapshot, setSnapshot] = useState(null);
  const [symbolSnapshots, setSymbolSnapshots] = useState({});
  const [bitOps, setBitOps] = useState([]);
  const [bitTail, setBitTail] = useState(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [lastUpdate, setLastUpdate] = useState("");

  const symbols = useMemo(() => SYMBOLS_BY_WORLD[world] || [], [world]);
  const currentTf = useMemo(() => tfForWorld(world, atlasMode), [world, atlasMode]);

  const activeAccent = useMemo(() => {
    if (world === "ATLAS_IA") return modeAccent(atlasMode);
    return WORLDS.find((w) => w.value === world)?.color || "#ff2fb3";
  }, [world, atlasMode]);

  useEffect(() => {
    if (world === "GAP") {
      setSymbol("XAUUSDz");
      return;
    }
    if (symbols.length && !symbols.includes(symbol)) {
      setSymbol(symbols[0]);
    }
  }, [world, symbols, symbol]);async function loadSnapshot() {
    const currentParams = new URLSearchParams({
      world,
      atlas_mode: atlasMode,
      symbol: symbol || "",
      tf: currentTf,
    });

    const currentData = await fetchJson(`/api/snapshot?${currentParams.toString()}`);
    setSnapshot(currentData);

    const list = Array.isArray(symbols) ? symbols : [];

    if (!list.length || world === "BITACORA") {
      setSymbolSnapshots({});
      setLastUpdate(new Date().toLocaleTimeString());
      return;
    }

    const requests = list.map(async (sym) => {
      try {
        const params = new URLSearchParams({
          world,
          atlas_mode: atlasMode,
          symbol: sym,
          tf: tfForWorld(world, atlasMode),
        });

        const data = await fetchJson(`/api/snapshot?${params.toString()}`);

        const row =
          (Array.isArray(data?.ui?.rows) ? data.ui.rows.find((r) => r?.symbol === sym) : null) ||
          {
            symbol: sym,
            state: data?.analysis?.status || "SIN_SETUP",
            score: data?.analysis?.score || 0,
          };

        return [sym, row];
      } catch {
        return [
          sym,
          {
            symbol: sym,
            state: "SIN_SETUP",
            score: 0,
          },
        ];
      }
    });

    const results = await Promise.all(requests);
    setSymbolSnapshots(Object.fromEntries(results));
    setLastUpdate(new Date().toLocaleTimeString());
  }

  async function loadBitacora() {
    try {
      const mode = bitacoraMode;
      const [opsRes, tailRes] = await Promise.allSettled([
        fetchJson(`/api/bitacora/ops?mode=${encodeURIComponent(mode)}`),
        fetchJson(`/api/bitacora/tail?mode=${encodeURIComponent(mode)}`),
      ]);

      setBitOps(opsRes.status === "fulfilled" ? normalizeBitOps(opsRes.value) : []);
      setBitTail(tailRes.status === "fulfilled" ? tailRes.value : null);
    } catch {
      setBitOps([]);
      setBitTail(null);
    }
  }

  async function refreshAll() {
    try {
      setError("");
      if (world === "BITACORA") {
        await loadBitacora();
      } else {
        await loadSnapshot();
      }
    } catch (err) {
      console.error(err);
      setError(err?.message || "Error cargando ATLAS");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    setLoading(true);
    refreshAll();

    const id = setInterval(() => {
      refreshAll();
    }, 2000);

    return () => clearInterval(id);
  }, [world, atlasMode, bitacoraMode, symbol]);

  const rawRows = useMemo(() => {
    const maybeRows = snapshot?.ui?.rows;
    return Array.isArray(maybeRows) ? maybeRows : [];
  }, [snapshot]);

  const rows = useMemo(() => {
    if (world === "ATLAS_IA") {
      return rawRows.filter((row) => Number(row?.score) >= 9);
    }
    return rawRows;
  }, [rawRows, world]);

  const visibleRows = useMemo(() => {
    if (world === "GAP") {
      return rows.length ? [rows[0]] : [];
    }
    return rows;
  }, [rows, world]);

  const analysis = snapshot?.analysis || {};
  const control = snapshot?.control || {};
  const frozenPlans = control?.frozen_plans ?? 0;
  const traffic = atlasTrafficLight(rows, analysis, activeAccent);

  const symbolStateMap = useMemo(() => {
    const rowsFromSymbols = Object.values(symbolSnapshots || {});
    return buildSymbolStateMap(rowsFromSymbols, symbols);
  }, [symbolSnapshots, symbols]);

  const activeRow = useMemo(() => {
    return visibleRows.find((r) => r?.symbol === symbol) || visibleRows[0] || null;
  }, [visibleRows, symbol]);

  const summary = useMemo(
    () => buildAnalysisSummary({ row: activeRow, analysis, atlasMode, currentTf, world }),
    [activeRow, analysis, atlasMode, currentTf, world]
  );

  const bitRows = useMemo(() => bitOps.map(extractBitItem), [bitOps]);

  const bitTotals = useMemo(() => {
    const totalUsd = bitRows.reduce((acc, row) => {
      const v = computeDerivedUsd(row);
      return acc + (Number.isFinite(v) ? v : 0);
    }, 0);

    const totalPips = bitRows.reduce((acc, row) => {
      const v = computeDerivedPips(row);
      return acc + (Number.isFinite(v) ? v : 0);
    }, 0);

    return {
      totalUsd,
      totalPips,
      count: bitRows.length,
    };
  }, [bitRows]);

  const renderMainTable = () => (
    <div style={styles.tableWrap}>
      <table style={styles.table}>
        <thead>
          <tr>
            <th style={styles.th}>SYMBOL</th>
            <th style={styles.th}>TF</th>
            <th style={styles.th}>SCORE</th>
            <th style={styles.th}>SIDE</th>
            <th style={styles.th}>STATE</th>
            <th style={styles.th}><HeaderChip label="ENTRY" color={activeAccent} /></th>
            <th style={styles.th}><HeaderChip label="SL" color="#ff6b6b" /></th>
            <th style={styles.th}><HeaderChip label="TP" color="#63c787" /></th>
            <th style={styles.th}><HeaderChip label="TP1" color="#f0b35a" /></th>
            <th style={styles.th}><HeaderChip label="LOT" color="#9fb3c8" /></th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <tr>
              <td colSpan={10} style={styles.emptyCell}>Cargando...</td>
            </tr>
          ) : visibleRows.length === 0 ? (
            <tr>
              <td colSpan={10} style={styles.emptyCell}>Sin setups de alta calidad.</td>
            </tr>
          ) : (
            visibleRows.map((row, index) => {
              const digits = decimalsBySymbol(row?.symbol);
              const parcial = row?.parcial ?? row?.partial ?? row?.tp1 ?? null;
              const lot = Number.isFinite(Number(row?.lot)) ? Number(row.lot) : null;

              return (
                <tr key={`${row?.symbol}-${row?.tf}-${index}`} style={styles.tr}>
                  <td style={styles.td}>
                    <button onClick={() => setSymbol(row.symbol)} style={styles.linkBtn}>
                      {row.symbol}
                    </button>
                  </td>
                  <td style={styles.td}>{row.tf || "-"}</td>
                  <td style={styles.td}>{formatNumber(row.score, 0)}</td>
                  <td style={styles.td}>
                    <span style={sideBadgeStyle(row?.side)}>{row?.side || "-"}</span>
                  </td>
                  <td style={styles.td}>
                    <span style={stateBadgeStyle(row?.state)}>{stateLabel(row?.state)}</span>
                  </td>
                  <td style={styles.td}>{formatNumber(row.entry, digits)}</td>
                  <td style={styles.td}>{formatNumber(row.sl, digits)}</td>
                  <td style={styles.td}>{formatNumber(row.tp, digits)}</td>
                  <td style={styles.td}>{formatNumber(parcial, digits)}</td>
                  <td style={styles.td}>{formatNumber(lot, 2)}</td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );const renderBitacora = () => (
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
          <KpiBox label="REGISTROS" value={String(bitTotals.count)} />
          <KpiBox label="PIPS Σ" value={formatSigned(bitTotals.totalPips, 1)} />
          <KpiBox label="USD Σ" value={formatSigned(bitTotals.totalUsd, 2)} />
        </div>
      </section>

      <div style={styles.bitGrid}>
        <div style={styles.cardBitBig}>
          <div style={styles.cardTitle}>OPERACIONES</div>
          <div style={styles.tableWrap}>
            <table style={styles.table}>
              <thead>
                <tr>
                  {["TIME", "EVENT", "SYMBOL", "TF", "SIDE", "STATE", "ENTRY", "SL", "TP", "TP1", "PIPS", "USD"].map((c) => (
                    <th key={c} style={styles.th}>{c}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {!bitRows.length ? (
                  <tr>
                    <td colSpan={12} style={styles.emptyCell}>Sin datos</td>
                  </tr>
                ) : (
                  bitRows.slice(-250).reverse().map((row, i) => {
                    const digits = decimalsBySymbol(row?.symbol);
                    const pips = computeDerivedPips(row);
                    const usd = computeDerivedUsd(row);

                    return (
                      <tr key={i} style={styles.tr}>
                        <td style={styles.td}>{row.ts}</td>
                        <td style={styles.td}>{row.event}</td>
                        <td style={styles.td}>{row.symbol}</td>
                        <td style={styles.td}>{row.tf}</td>
                        <td style={styles.td}>
                          <span style={sideBadgeStyle(row.side)}>{row.side || "-"}</span>
                        </td>
                        <td style={styles.td}>
                          <span style={stateBadgeStyle(row.state)}>{stateLabel(row.state)}</span>
                        </td>
                        <td style={styles.td}>{formatNumber(row.entry, digits)}</td>
                        <td style={styles.td}>{formatNumber(row.sl, digits)}</td>
                        <td style={styles.td}>{formatNumber(row.tp, digits)}</td>
                        <td style={styles.td}>{formatNumber(row.parcial, digits)}</td>
                        <td style={styles.td}>{formatSigned(pips, 1)}</td>
                        <td style={styles.td}>
                          <span style={usdBadgeStyle(usd)}>{formatSigned(usd, 2)}</span>
                        </td>
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

            <StatusPill label="FREEZE" value={String(frozenPlans)} active={frozenPlans > 0} accent={activeAccent} />
            <StatusPill label="UPDATE" value={lastUpdate || "-"} active={false} accent={activeAccent} />
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
                    const accent = modeAccent(item.value);
                    return (
                      <button
                        key={item.value}
                        onClick={() => setAtlasMode(item.value)}
                        style={{
                          ...styles.segBtn,
                          ...(atlasMode === item.value
                            ? {
                                background: withAlpha(accent, 0.22),
                                border: `1px solid ${withAlpha(accent, 0.52)}`,
                                color: "#ffffff",
                                boxShadow: `0 0 0 1px ${withAlpha(accent, 0.12)} inset`,
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
                    {world} - {world === "ATLAS_IA" ? atlasMode : "-"} - {stateLabel(analysis?.status || "SIN_SETUP")} - {currentTf}
                  </div>
                </div>
              </div>

              <div style={styles.chartFrame}>
                <Charts snapshot={snapshot} activeRow={activeRow} accent={activeAccent} />
              </div>
            </section>

            <section
              style={{
                ...styles.card,
                boxShadow: `0 0 0 1px ${withAlpha(activeAccent, 0.10)}, 0 14px 34px rgba(0,0,0,0.18)`,
              }}
            >
              {renderMainTable()}
            </section>

            <section
              style={{
                ...styles.analysisPanel,
                boxShadow: `0 0 0 1px ${withAlpha(activeAccent, 0.10)}, 0 12px 28px rgba(0,0,0,0.16)`,
              }}
            >
              <div style={styles.analysisHeader}>
                <div style={styles.analysisTitle}>LECTURA ATLAS</div>
                <div style={styles.analysisMini}>{summary.titulo}</div>
              </div>

              <div style={styles.analysisNarrative}>
                {summary.texto}
              </div>
            </section>
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
  statusPill: { minWidth: 108, borderRadius: 12, padding: "8px 10px", display: "grid", gap: 2, border: "1px solid rgba(255,255,255,0.08)" },
  statusPillOff: { background: "rgba(255,255,255,0.035)" },
  statusLabel: { fontSize: 10, opacity: 0.72, letterSpacing: 0.55, fontWeight: 700 },
  statusValue: { fontSize: 12, fontWeight: 800 },
  trafficBox: { minWidth: 260, borderRadius: 14, padding: "10px 14px", background: "rgba(255,255,255,0.04)" },
  trafficMain: { fontSize: 18, fontWeight: 900, lineHeight: 1.1 },
  trafficSub: { marginTop: 4, fontSize: 12, opacity: 0.78, maxWidth: 340, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" },
  controlsSection: { display: "grid", gap: 12, padding: 14, borderRadius: 18, border: "1px solid rgba(255,255,255,0.08)", background: "rgba(255,255,255,0.022)" },
  compactGrid: { display: "grid", gridTemplateColumns: "1fr", gap: 12 },
  controlBlock: { display: "grid", gap: 8 },
  blockLabel: { fontSize: 11, opacity: 0.68, letterSpacing: 0.8, fontWeight: 800 },
  segmented: { display: "flex", gap: 8, flexWrap: "wrap" },
  segBtn: { borderRadius: 11, padding: "9px 12px", background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", color: "#eef3fb", fontSize: 12, fontWeight: 800, cursor: "pointer", transition: "all 120ms ease" },
  symbolGrid: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(104px, 1fr))", gap: 8 },
  symbolBtn: { borderRadius: 11, padding: "10px 10px", background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", color: "#eef3fb", fontSize: 12, fontWeight: 800, cursor: "pointer", transition: "all 120ms ease" },
  errorBox: { marginTop: 2, padding: "10px 12px", borderRadius: 12, border: "1px solid rgba(255,120,120,0.30)", background: "rgba(255,120,120,0.10)", color: "#ffc9c9", fontSize: 12, fontWeight: 700 },
  chartSection: { display: "grid", gap: 10, padding: 14, borderRadius: 18, border: "1px solid rgba(255,255,255,0.08)", background: "rgba(255,255,255,0.022)" },
  chartTopbar: { display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", alignItems: "flex-start" },
  instrument: { fontSize: 28, fontWeight: 900, lineHeight: 1 },
  instrumentMeta: { marginTop: 6, fontSize: 14, color: "#d0d9e8", fontWeight: 700 },
  chartFrame: { overflow: "hidden", borderRadius: 16, border: "1px solid rgba(255,255,255,0.08)" },
  analysisPanel: { display: "grid", gap: 10, padding: 14, borderRadius: 16, border: "1px solid rgba(255,255,255,0.08)", background: "rgba(255,255,255,0.02)" },
  analysisHeader: { display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap", alignItems: "center" },
  analysisTitle: { fontSize: 15, fontWeight: 900, letterSpacing: 0.4 },
  analysisMini: { fontSize: 12, color: "#c8d4e6", fontWeight: 700 },
  analysisNarrative: { fontSize: 14, lineHeight: 1.55, color: "#eef3fb", padding: "10px 12px", borderRadius: 14, background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" },
  card: { display: "grid", gap: 10, padding: 14, borderRadius: 18, border: "1px solid rgba(255,255,255,0.08)", background: "rgba(255,255,255,0.022)" },
  bitWrap: { display: "grid", gap: 16 },
  bitTopRow: { display: "flex", justifyContent: "space-between", gap: 16, flexWrap: "wrap", alignItems: "center" },
  kpiStrip: { display: "flex", gap: 8, flexWrap: "wrap" },
  kpiBox: { minWidth: 96, borderRadius: 12, padding: "8px 10px", border: "1px solid rgba(255,255,255,0.08)", background: "rgba(255,255,255,0.03)" },
  kpiLabel: { fontSize: 10, opacity: 0.65, letterSpacing: 0.65, fontWeight: 800 },
  kpiValue: { marginTop: 4, fontSize: 12, fontWeight: 800 },
  bitGrid: { display: "grid", gridTemplateColumns: "1.35fr 0.85fr", gap: 16 },
  cardBitBig: { display: "grid", gap: 12, padding: 18, borderRadius: 20, border: "1px solid rgba(183,132,255,0.18)", background: "rgba(255,255,255,0.022)", boxShadow: "0 0 0 1px rgba(183,132,255,0.08), 0 16px 38px rgba(0,0,0,0.18)" },
  cardBitSide: { display: "grid", gap: 12, padding: 18, borderRadius: 20, border: "1px solid rgba(183,132,255,0.18)", background: "rgba(255,255,255,0.022)", boxShadow: "0 0 0 1px rgba(183,132,255,0.08), 0 16px 38px rgba(0,0,0,0.18)" },
  cardTitle: { fontSize: 16, fontWeight: 900, letterSpacing: 0.4 },
  tableWrap: { width: "100%", overflowX: "auto" },
  table: { width: "100%", minWidth: 1220, borderCollapse: "collapse" },
  th: { textAlign: "left", padding: "14px 14px", fontSize: 14, letterSpacing: 0.55, opacity: 0.82, borderBottom: "1px solid rgba(255,255,255,0.08)", fontWeight: 900, whiteSpace: "nowrap" },
  tr: { borderBottom: "1px solid rgba(255,255,255,0.06)" },
  td: { padding: "16px 14px", fontSize: 16, whiteSpace: "nowrap", color: "#eef3fb" },
  emptyCell: { padding: "22px 14px", fontSize: 16, opacity: 0.8 },
  badgeBase: { display: "inline-flex", alignItems: "center", justifyContent: "center", borderRadius: 999, padding: "7px 12px", fontSize: 13, fontWeight: 900 },
  linkBtn: { border: "none", background: "transparent", color: "#dce9ff", padding: 0, cursor: "pointer", fontSize: 16, fontWeight: 900 },
  preMajestic: { margin: 0, minHeight: 520, maxHeight: 820, overflow: "auto", padding: 14, borderRadius: 16, background: "#0b1118", border: "1px solid rgba(183,132,255,0.16)", color: "#e7dcf5", fontSize: 12, lineHeight: 1.45, whiteSpace: "pre-wrap", wordBreak: "break-word", boxShadow: "inset 0 0 0 1px rgba(183,132,255,0.06)" },
};