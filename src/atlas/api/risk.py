import os
from dataclasses import dataclass

@dataclass
class RiskPlan:
    lots: float
    sl: float
    tp: float

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def calc_lots_simple(symbol: str, entry: float, sl: float) -> float:
    # Simple placeholder: risk USD / (distance * point_value)
    # NOTE: For true point_value, read mt5.symbol_info().trade_tick_value etc.
    risk_usd = float(os.getenv("ATLAS_RISK_USD_PER_TRADE", "25"))
    dist = abs(entry - sl)
    if dist <= 0:
        return 0.01
    # naive point value approximation
    lots = risk_usd / (dist * 100.0)
    return clamp(lots, 0.01, 5.0)