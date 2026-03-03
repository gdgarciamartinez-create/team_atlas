from __future__ import annotations
from typing import List, Dict, Any

def in_zone(price: float, low: float, high: float, pad: float = 0.0) -> bool:
    lo = min(low, high) - pad
    hi = max(low, high) + pad
    return lo <= price <= hi

def detect_breakout_close(rates: List[Dict[str, Any]], level: float, direction: str) -> bool:
    if len(rates) < 3:
        return False
    c = rates[-1]["close"]
    prev_c = rates[-2]["close"]
    return (prev_c <= level and c > level) if direction == "buy" else (prev_c >= level and c < level)

def detect_pullback_reject(rates: List[Dict[str, Any]], zone_low: float, zone_high: float, direction: str) -> bool:
    if len(rates) < 4:
        return False
    last = rates[-1]
    prev = rates[-2]
    zlo, zhi = min(zone_low, zone_high), max(zone_low, zone_high)
    zr = max(1e-9, zhi - zlo)

    if direction == "buy":
        touched = last["low"] <= zhi and last["low"] >= zlo - zr * 0.2
        reject = last["close"] > last["open"] and last["close"] > prev["close"]
        return touched and reject
    else:
        touched = last["high"] >= zlo and last["high"] <= zhi + zr * 0.2
        reject = last["close"] < last["open"] and last["close"] < prev["close"]
        return touched and reject

def detect_momentum_continuation(rates: List[Dict[str, Any]], direction: str) -> bool:
    if len(rates) < 6:
        return False
    last = rates[-1]
    a = rates[-5]
    b = rates[-3]
    if direction == "buy":
        return (b["close"] > a["open"]) and (last["close"] > b["close"])
    else:
        return (b["close"] < a["open"]) and (last["close"] < b["close"])

def fib_ok_placeholder() -> bool:
    return True
