# src/atlas/bot/indicators.py
from __future__ import annotations

from typing import List, Optional, Tuple

def atr(candles: List[dict], n: int = 14) -> Optional[float]:
    if not candles or len(candles) < n + 1:
        return None
    trs = []
    for i in range(-n, 0):
        cur = candles[i]
        prev = candles[i - 1]
        high = float(cur["high"])
        low = float(cur["low"])
        prev_close = float(prev["close"])
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
    return sum(trs) / len(trs) if trs else None

def rsi(candles: List[dict], n: int = 14) -> Optional[float]:
    if not candles or len(candles) < n + 1:
        return None
    gains = 0.0
    losses = 0.0
    for i in range(-n, 0):
        diff = float(candles[i]["close"]) - float(candles[i - 1]["close"])
        if diff >= 0:
            gains += diff
        else:
            losses += abs(diff)
    if losses == 0:
        return 100.0
    rs = (gains / n) / (losses / n)
    return 100.0 - (100.0 / (1.0 + rs))

def trend_dir(candles: List[dict], lookback: int = 40) -> str:
    if not candles or len(candles) < 10:
        return "FLAT"
    sub = candles[-lookback:] if len(candles) >= lookback else candles[:]
    start = float(sub[0]["open"])
    end = float(sub[-1]["close"])
    if end > start:
        return "UP"
    if end < start:
        return "DOWN"
    return "FLAT"

def last_poi(candles: List[dict], window: int = 60) -> Tuple[Optional[float], Optional[float]]:
    """
    POI simple: último techo y último piso del rango reciente.
    """
    if not candles:
        return None, None
    sub = candles[-window:] if len(candles) >= window else candles[:]
    hi = max(float(c["high"]) for c in sub)
    lo = min(float(c["low"]) for c in sub)
    return hi, lo