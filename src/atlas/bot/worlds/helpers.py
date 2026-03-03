# src/atlas/bot/worlds/helpers.py
from __future__ import annotations

from typing import Any, Dict, List, Tuple


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _candle_ohlc(c: Dict[str, Any]) -> Tuple[float, float, float, float]:
    return (
        _safe_float(c.get("o"), 0.0),
        _safe_float(c.get("h"), 0.0),
        _safe_float(c.get("l"), 0.0),
        _safe_float(c.get("c"), 0.0),
    )


def _last_close(candles: List[Dict[str, Any]]) -> float:
    if not candles:
        return 0.0
    return _safe_float(candles[-1].get("c"), 0.0)


def _last_ts_ms(candles: List[Dict[str, Any]]) -> int:
    if not candles:
        return 0
    try:
        return int(candles[-1].get("t", 0))
    except Exception:
        return 0