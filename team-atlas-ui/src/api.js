const base = "/api";

async function j(url, init) {
  const r = await fetch(url, init);
  const txt = await r.text().catch(() => "");
  let data = null;
  try { data = txt ? JSON.parse(txt) : null; } catch { data = txt; }
  if (!r.ok) throw new Error(typeof data === "string" ? data : JSON.stringify(data));
  return data;
}

export const health = () => j(`${base}/health`);
export const listSetups = () => j(`${base}/setups`);
export const createSetup = (payload) =>
  j(`${base}/setups`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });

export const enableSetup = (id) => j(`${base}/setups/${id}/enable`, { method: "POST" });
export const disableSetup = (id) => j(`${base}/setups/${id}/disable`, { method: "POST" });
export const deleteSetup = (id) => j(`${base}/setups/${id}`, { method: "DELETE" });

export const listAlerts = () => j(`${base}/alerts`);
