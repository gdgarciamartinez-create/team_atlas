const API = import.meta.env.VITE_API_BASE || "/api";

async function safeJson(r) {
  const t = await r.text();
  try { return JSON.parse(t); }
  catch { throw new Error(`No JSON: ${t.slice(0, 200)}`); }
}

export async function getSnapshot({ symbol = "XAUUSD", tf = "M1", world = "GENERAL" }) {
  const qs = new URLSearchParams({ symbol, tf, strategy: world });
  const r = await fetch(`${API}/snapshot?${qs.toString()}`);
  if (!r.ok) throw new Error(`snapshot HTTP ${r.status}`);
  return safeJson(r);
}

export async function getEnums() {
  const r = await fetch(`${API}/enums`);
  if (!r.ok) throw new Error(`enums HTTP ${r.status}`);
  return safeJson(r);
}

export async function setWorldAlert(world, enabled) {
  const qs = new URLSearchParams({ world, enabled: String(enabled) });
  const r = await fetch(`${API}/alerts/world?${qs.toString()}`, { method: "POST" });
  if (!r.ok) throw new Error(`alerts/world HTTP ${r.status}`);
  return safeJson(r);
}

export async function telegramStatus() {
  const r = await fetch(`${API}/telegram/status`);
  if (!r.ok) throw new Error(`telegram/status HTTP ${r.status}`);
  return safeJson(r);
}

export async function telegramTest() {
  const r = await fetch(`${API}/telegram/test`, { method: "POST" });
  if (!r.ok) throw new Error(`telegram/test HTTP ${r.status}`);
  return safeJson(r);
}