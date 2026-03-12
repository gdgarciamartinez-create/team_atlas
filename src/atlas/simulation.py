# src/atlas/simulation.py
from __future__ import annotations

from typing import Any, Dict, List


def _to_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _get_ohlc(c: Any, key1: str, key2: str) -> float:
    """
    Soporta:
    - dict con 'o/h/l/c'
    - dict con 'open/high/low/close'
    """
    if isinstance(c, dict):
        return _to_float(c.get(key1, c.get(key2, 0.0)))
    return 0.0


def calculate_poi(candles: List[Dict[str, Any]], *, lookback: int = 80) -> Dict[str, Any]:
    """
    POI simple y estable para no romper el backend:
    - toma las últimas N velas
    - calcula hi/lo del rango y devuelve el mid como poi

    Retorna dict SIEMPRE (ok True/False).
    """
    if not isinstance(candles, list) or len(candles) < 5:
        return {
            "ok": False,
            "reason": "NOT_ENOUGH_CANDLES",
            "poi": 0.0,
            "hi": 0.0,
            "lo": 0.0,
            "last": 0.0,
            "lookback": int(lookback),
        }

    n = max(5, int(lookback))
    use = candles[-n:]

    hi = max(_get_ohlc(x, "h", "high") for x in use)
    lo = min(_get_ohlc(x, "l", "low") for x in use)
    last = _get_ohlc(use[-1], "c", "close")

    poi = (hi + lo) / 2.0

    return {
        "ok": True,
        "poi": poi,
        "hi": hi,
        "lo": lo,
        "last": last,
        "lookback": n,
    }