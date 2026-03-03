export async function getArmed() {
  const res = await fetch("/api/exec/armed");
  return res.json();
}
export async function setArmed(armed) {
  const res = await fetch("/api/exec/armed", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ armed }),
  });
  return res.json();
}
export async function placeOrder({ symbol, side, lots, sl, tp }) {
  const res = await fetch("/api/exec/place", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbol, side, lots, sl, tp }),
  });
  return res.json();
}