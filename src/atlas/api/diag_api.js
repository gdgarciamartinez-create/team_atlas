export async function auditTail(limit=200){
  const r = await fetch(`/api/audit/tail?limit=${limit}`);
  return r.json();
}
export async function auditBySymbol(symbol, limit=200){
  const r = await fetch(`/api/audit/symbol?symbol=${encodeURIComponent(symbol)}&limit=${limit}`);
  return r.json();
}
export async function replay(event_id){
  const r = await fetch(`/api/audit/replay`, {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({event_id})});
  return r.json();
}