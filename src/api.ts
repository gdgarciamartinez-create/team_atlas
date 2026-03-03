export type Setup = {
  id: string;
  symbol: string;
  direction: "buy" | "sell";
  zone_low: number;
  zone_high: number;
  tfs: string[];
  mode: string;
  notes?: string | null;
  enabled: boolean;
  created_at?: string | null;
};

export type AlertMsg = {
  id: string;
  ts: string;
  symbol: string;
  mode: string;
  direction: string;
  tf: string;
  gatillo: string;
  entry: number | null;
  sl: number | null;
  tp1: number | null;
  tp2: number | null;
  lot: number | null;
  partial: string | null;
  rr: number | null;
  reason: string | null;
};

// Usar variable de entorno VITE_ o fallback a localhost:8001
const base = "http://127.0.0.1:8001";

async function j<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init);
  if (!r.ok) {
    const txt = await r.text().catch(() => "");
    throw new Error(`${r.status} ${r.statusText} :: ${txt}`);
  }
  return (await r.json()) as T;
}

export function health() {
  return j<{ ok: boolean; app: string }>(`${base}/health`);
}

export function listSetups() {
  return j<Setup[]>(`${base}/setups`);
}

export function createSetup(payload: Omit<Setup, "id" | "enabled" | "created_at"> & { enabled?: boolean }) {
  return j<Setup>(`${base}/setups`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function enableSetup(id: string) {
  return j<{ ok: boolean; setup_id: string; enabled: boolean }>(`${base}/setups/${id}/enable`, { method: "POST" });
}

export function disableSetup(id: string) {
  return j<{ ok: boolean; setup_id: string; enabled: boolean }>(`${base}/setups/${id}/disable`, { method: "POST" });
}

export function deleteSetup(id: string) {
  return j<{ ok: boolean; setup_id: string }>(`${base}/setups/${id}`, { method: "DELETE" });
}

export function listAlerts() {
  return j<AlertMsg[]>(`${base}/alerts`);
}