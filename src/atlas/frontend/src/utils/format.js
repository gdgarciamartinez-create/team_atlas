// src/atlas/frontend/src/utils/format.js
// Utilidades de formato + validación horaria Santiago (frontend).
// Objetivo: que nunca se rompa por timezone y que la UI tenga criterios estrictos y consistentes.

const TZ = "America/Santiago";

/** Devuelve partes numéricas (YYYY, MM, DD, hh, mm, ss) en zona Santiago para un ts_ms */
function partsSCL(ts_ms) {
  const d = new Date(Number(ts_ms || Date.now()));
  // Usamos formatToParts para evitar depender del locale y parseos frágiles.
  const fmt = new Intl.DateTimeFormat("en-CA", {
    timeZone: TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
  const out = {};
  for (const p of fmt.formatToParts(d)) {
    if (p.type !== "literal") out[p.type] = p.value;
  }
  return {
    y: Number(out.year),
    mo: Number(out.month),
    da: Number(out.day),
    hh: Number(out.hour),
    mm: Number(out.minute),
    ss: Number(out.second),
  };
}

/** "YYYY-MM-DD HH:mm:ss" en Santiago */
export function fmtDateTimeSantiago(ts_ms) {
  const p = partsSCL(ts_ms);
  const pad = (n) => String(n).padStart(2, "0");
  return `${p.y}-${pad(p.mo)}-${pad(p.da)} ${pad(p.hh)}:${pad(p.mm)}:${pad(p.ss)}`;
}

/** Unix seconds -> "HH:mm:ss" en Santiago */
export function fmtTimeSantiagoFromUnixSec(unixSec) {
  const ts = Number(unixSec || 0) * 1000;
  const p = partsSCL(ts);
  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(p.hh)}:${pad(p.mm)}:${pad(p.ss)}`;
}

/** Helpers de ventanas (estrictas, por reloj Santiago) */
function isBetweenMinutes(hh, mm, startH, startM, endH, endM) {
  const t = hh * 60 + mm;
  const a = startH * 60 + startM;
  const b = endH * 60 + endM;
  return t >= a && t <= b; // INCLUSIVO estricto
}

/**
 * PRESESIÓN: 07:00–11:00 Santiago (estricto).
 * Nota: el usuario pidió 7 a 11 y que a las 11 "se apaga todo".
 */
export function isInPresesionWindowSantiago(ts_ms) {
  const p = partsSCL(ts_ms);
  return isBetweenMinutes(p.hh, p.mm, 7, 0, 11, 0);
}

export function presesionWindowLabel() {
  return "07:00–11:00 Santiago";
}

/**
 * GAP XAUUSD: verano apertura 20:00 (Santiago).
 * Ventana detección/operativa: 19:55–20:30 (estricto).
 * (Si más adelante querés 2 modos invierno/verano automático, lo agregamos,
 *  pero por ahora dejamos EXACTO lo que pediste: verano=20:00)
 */
export function isInGapWindowSantiago(ts_ms) {
  const p = partsSCL(ts_ms);
  return isBetweenMinutes(p.hh, p.mm, 19, 55, 20, 30);
}

export function gapWindowLabel() {
  return "19:55–20:30 Santiago (apertura ~20:00)";
}

/** --- Decimales / precios --- */
export function priceDecimals(symbol) {
  const s = String(symbol || "").toUpperCase();
  // Oro y Oil típicamente 2 decimales (dependiendo broker, pero UI base)
  if (s.includes("XAU")) return 2;
  if (s.includes("XAG")) return 3;
  if (s.includes("USOIL") || s.includes("WTI") || s.includes("BRENT")) return 2;
  // Índices suelen 1 o 2 (depende), dejamos 1 por defecto
  if (s.includes("USTEC") || s.includes("NAS") || s.includes("US30") || s.includes("SPX")) return 1;
  // Forex 5 dígitos típicos, JPY 3
  if (s.includes("JPY")) return 3;
  return 5;
}

export function fmtPrice(symbol, value) {
  const v = Number(value);
  if (!Number.isFinite(v)) return "—";
  const dec = priceDecimals(symbol);
  return v.toFixed(dec);
}

/** --- Riesgo y lotaje (estimación UI) --- */
export function riskUsd(balanceUsd, riskPct) {
  const bal = Number(balanceUsd);
  const pct = Number(riskPct);
  if (!Number.isFinite(bal) || !Number.isFinite(pct)) return 0;
  return Math.max(0, bal * (pct / 100));
}

/**
 * Estimación simple de lotaje (UI):
 * lot ≈ riesgoUsd / (distanciaPrecio * valorPorUnidad)
 * Como cada símbolo tiene contrato distinto, lo hacemos "safe":
 * - Si faltan datos, devuelve null.
 * - Para XAU (aprox): 1.00 lote ≈ 100 oz. $1 de movimiento ≈ $100 por lote.
 * - Para Forex (aprox): 1 pip ≈ $10 por lote estándar (en pares xxxUSD). Si no es xxxUSD, esto es aproximación.
 */
export function estimateLot({ symbol, entry, sl, balanceUsd, riskPct }) {
  const s = String(symbol || "");
  const e = Number(entry);
  const stop = Number(sl);
  const ru = riskUsd(balanceUsd, riskPct);

  if (!s || !Number.isFinite(e) || !Number.isFinite(stop) || !(ru > 0)) return null;

  const dist = Math.abs(e - stop);
  if (!(dist > 0)) return null;

  const up = s.toUpperCase();

  // XAUUSD aproximación: $1 move = $100 por 1 lote (100 oz).
  if (up.includes("XAU")) {
    const dollarsPerLotPer1 = 100; // aproximado
    const riskPerLot = dist * dollarsPerLotPer1;
    if (!(riskPerLot > 0)) return null;
    return ru / riskPerLot;
  }

  // Forex aproximación por pip (muy general)
  const dec = priceDecimals(up);
  const pip = up.includes("JPY") ? 0.01 : 0.0001;
  const pips = dist / pip;

  // $10 por pip por lote (aprox en majors)
  const usdPerPipPerLot = 10;
  const riskPerLot = pips * usdPerPipPerLot;
  if (!(riskPerLot > 0)) return null;
  return ru / riskPerLot;
}
