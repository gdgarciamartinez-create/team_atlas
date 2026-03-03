# src/atlas/bot/patterns.py
from __future__ import annotations

from typing import List, Optional

def last_engulfing(candles: List[dict]) -> Optional[str]:
    if not candles or len(candles) < 2:
        return None
    a = candles[-2]
    b = candles[-1]
    a_o, a_c = float(a["open"]), float(a["close"])
    b_o, b_c = float(b["open"]), float(b["close"])

    # bullish engulf
    if a_c < a_o and b_c > b_o and b_o <= a_c and b_c >= a_o:
        return "BULL_ENGULF"
    # bearish engulf
    if a_c > a_o and b_c < b_o and b_o >= a_c and b_c <= a_o:
        return "BEAR_ENGULF"
    return None

def last_pinbar(candles: List[dict]) -> Optional[str]:
    if not candles:
        return None
    c = candles[-1]
    o, h, l, cl = float(c["open"]), float(c["high"]), float(c["low"]), float(c["close"])
    body = abs(cl - o)
    upper = h - max(o, cl)
    lower = min(o, cl) - l
    # pinbar simple
    if lower > body * 2 and upper < body * 1.2:
        return "BULL_PIN"
    if upper > body * 2 and lower < body * 1.2:
        return "BEAR_PIN"
    return None