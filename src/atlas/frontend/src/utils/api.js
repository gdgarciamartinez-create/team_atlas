// src/atlas/frontend/src/utils/api.js
export async function fetchStatus() {
  const r = await fetch("/api/status");
  return await r.json();
}

export async function fetchSnapshot({ world, symbol, tf, count }) {
  const p = new URLSearchParams({
    world,
    symbol,
    tf,
    count: String(count ?? 220),
  });
  const r = await fetch(`/api/snapshot?${p.toString()}`);
  return await r.json();
}
