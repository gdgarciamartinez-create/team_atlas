from __future__ import annotations
from typing import Dict, Any, List, Tuple, Optional

def _swing_hi_lo(candles: List[Dict[str, float]], lookback: int = 120) -> Optional[Tuple[float, float]]:
    if not candles:
        return None
    chunk = candles[-lookback:] if len(candles) > lookback else candles
    hi = max(c["high"] for c in chunk)
    lo = min(c["low"] for c in chunk)
    if hi == lo:
        return None
    return hi, lo

def fibo_0_786_zone(candles: List[Dict[str, float]], direction: str) -> Dict[str, Any]:
    """
    direction: "UP" o "DOWN"
    Retorna zona [low, high] de 0.786–0.79
    """
    sw = _swing_hi_lo(candles)
    if not sw:
        return {"ok": False, "reason": "NO_SWING", "level": 0.786, "zone": None, "swing": None}

    hi, lo = sw
    rng = hi - lo
    if direction == "UP":
        lvl_786 = hi - rng * 0.786
        lvl_790 = hi - rng * 0.79
    else:
        lvl_786 = lo + rng * 0.786
        lvl_790 = lo + rng * 0.79

    z_low = float(min(lvl_786, lvl_790))
    z_high = float(max(lvl_786, lvl_790))
    return {"ok": True, "level": 0.786, "zone": [z_low, z_high], "swing": {"hi": float(hi), "lo": float(lo)}}

def touched_zone_last(candles: List[Dict[str, float]], zone: List[float], last_n: int = 12) -> bool:
    if not candles or not zone:
        return False
    z_low, z_high = float(zone[0]), float(zone[1])
    chunk = candles[-last_n:] if len(candles) > last_n else candles
    for c in chunk:
        if c["low"] <= z_high and c["high"] >= z_low:
            return True
    return False

def closes_outside_zone_against(candles: List[Dict[str, float]], zone: List[float], side: str) -> bool:
    """
    Regla dura: dos cierres consecutivos con cuerpo fuera de zona INVALIDAN hipótesis contraria.
    side=BUY: invalida si hay 2 cierres seguidos por debajo de z_low
    side=SELL: invalida si hay 2 cierres seguidos por encima de z_high
    """
    if not candles or len(candles) < 3 or not zone:
        return False
    z_low, z_high = float(zone[0]), float(zone[1])
    c1 = candles[-1]["close"]
    c2 = candles[-2]["close"]
    if (side or "").upper() == "BUY":
        return (c1 < z_low) and (c2 < z_low)
    return (c1 > z_high) and (c2 > z_high)