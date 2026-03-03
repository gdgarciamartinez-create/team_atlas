from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple
from .data_source import Candle

@dataclass
class TradePlan:
    entry: float
    sl: float
    tps: List[float]
    risk_pct: float = 2.0

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def build_plan(
    candles: List[Candle],
    direction: str,
    zone: Tuple[float,float],
    fib_levels: dict,
) -> Optional[TradePlan]:
    """
    Reglas:
    - entry: close actual, pero clamp dentro de zona
    - SL: detrás del extremo de últimas 6 velas (técnico)
    - TPs: escalones fibo (0.618/0.382/0.236/0.0) del fib_levels
    - Si falta algo => None (NO inventar)
    """
    if not candles or len(candles) < 20:
        return None
    if not fib_levels or zone == (0.0,0.0):
        return None

    last = candles[-1].c
    zlo, zhi = zone
    entry = clamp(last, zlo, zhi)

    if direction == "BUY":
        sl = min(c.l for c in candles[-6:])
        # SL debe estar debajo de entry
        if sl >= entry:
            sl = min(c.l for c in candles[-12:])
        if sl >= entry:
            return None
        # TPs: niveles hacia arriba
        need = ["0.618","0.382","0.236","0.0"]
        if any(k not in fib_levels for k in need):
            return None
        tps = [fib_levels["0.618"], fib_levels["0.382"], fib_levels["0.236"], fib_levels["0.0"]]
        tps = [tp for tp in tps if tp > entry]
        if not tps:
            return None
    elif direction == "SELL":
        sl = max(c.h for c in candles[-6:])
        if sl <= entry:
            sl = max(c.h for c in candles[-12:])
        if sl <= entry:
            return None
        need = ["0.618","0.382","0.236","0.0"]
        if any(k not in fib_levels for k in need):
            return None
        tps = [fib_levels["0.618"], fib_levels["0.382"], fib_levels["0.236"], fib_levels["0.0"]]
        tps = [tp for tp in tps if tp < entry]
        if not tps:
            return None
    else:
        return None

    return TradePlan(entry=float(round(entry, 5)), sl=float(round(sl, 5)), tps=[float(round(x, 5)) for x in tps], risk_pct=2.0)