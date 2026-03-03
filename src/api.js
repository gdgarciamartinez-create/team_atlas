export const API_BASE = "/api";

// ---- existing ----
export async function getPresesionBoard() {
  const res = await fetch(`${API_BASE}/presesion/board`);
  if (!res.ok) throw new Error("Presesion error");
  return res.json();
}

export async function getBotStatus() {
  const res = await fetch(`${API_BASE}/bot/status`);
  return res.json();
}

export async function getBotMetrics() {
  const res = await fetch(`${API_BASE}/bot/metrics`);
  return res.json();
}

export async function getBotLogs() {
  const res = await fetch(`${API_BASE}/bot/logs`);
  return res.json();
}

// ✅ NEW: snapshot (candles reales)
export async function getSnapshot({ world, symbol, tf, count, atlas_mode }) {
  const params = new URLSearchParams({
    world,
    symbol,
    tf,
    count: String(count ?? 200),
  });

  if (world === "ATLAS_IA" && atlas_mode) {
    params.set("atlas_mode", atlas_mode);
  }

  const res = await fetch(`${API_BASE}/snapshot?${params.toString()}`);
  if (!res.ok) throw new Error(`Snapshot HTTP ${res.status}`);
  const data = await res.json();

  // ✅ IMPORTANTE: candles debe ser ARRAY
  const candles = Array.isArray(data?.candles) ? data.candles : [];

  return {
    ...data,
    candles,                 // ✅ array real
    candles_count: candles.length, // ✅ número aparte si querés mostrar
  };
}
