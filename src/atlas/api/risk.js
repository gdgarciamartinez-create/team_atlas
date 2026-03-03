export function approxPips(symbol, entry, price) {
  if (entry == null || price == null) return null;
  const d = Math.abs(price - entry);
  // FX majors: 0.0001, JPY: 0.01, Gold: 0.1, Nasdaq: 1
  let pip = 0.0001;
  if (symbol.includes("JPY")) pip = 0.01;
  if (symbol.includes("XAU")) pip = 0.1;
  if (symbol.includes("NAS") || symbol.includes("NDX")) pip = 1;
  return d / pip;
}

export function lotSize({ balance, riskPct, slPips, pipValuePerLot }) {
  if (!balance || !riskPct || !slPips || !pipValuePerLot) return null;
  const riskMoney = balance * (riskPct / 100);
  const lots = riskMoney / (slPips * pipValuePerLot);
  return lots;
}