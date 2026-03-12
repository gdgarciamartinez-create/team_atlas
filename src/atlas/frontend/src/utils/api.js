// src/atlas/frontend/src/utils/api.js

export async function fetchStatus() {
  const r = await fetch("/status");
  if (!r.ok) {
    throw new Error(`STATUS HTTP ${r.status}`);
  }
  return await r.json();
}

export async function fetchSnapshot({
  world = "ATLAS_IA",
  atlasMode = "SCALPING",
  symbol = "XAUUSDz",
  tf = "M1",
  count = 220,
} = {}) {
  const p = new URLSearchParams({
    world,
    atlas_mode: atlasMode,
    symbol,
    tf,
    count: String(count),
  });

  const r = await fetch(`/api/snapshot?${p.toString()}`);
  if (!r.ok) {
    throw new Error(`SNAPSHOT HTTP ${r.status}`);
  }

  return await r.json();
}