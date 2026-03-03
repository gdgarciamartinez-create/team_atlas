# src/atlas/mt5_provider.py
from __future__ import annotations

from typing import Any, Dict, List

from atlas.core.mt5_service import get_candles


def fetch_candles(symbol: str, tf: str, count: int) -> Dict[str, Any]:
    """
    Adapter único para snapshot_core.
    - llama a tu mt5_service.get_candles()
    - normaliza velas a: t,o,h,l,c,v
    """
    result = get_candles(symbol=symbol, tf=tf, count=count)

    if not isinstance(result, dict):
        return {"candles": [], "last_error": ["E_MT5_FORMAT", "Invalid MT5 response (not dict)"]}

    raw = result.get("candles", []) or []
    last_error = result.get("last_error", [1, "Success"])

    candles: List[Dict[str, Any]] = []
    for c in raw:
        # Soporta ambos formatos:
        # - MT5 directo: time/open/high/low/close/tick_volume
        # - ya-normalizado: t/o/h/l/c/v
        t = c.get("t", c.get("time"))
        o = c.get("o", c.get("open"))
        h = c.get("h", c.get("high"))
        l = c.get("l", c.get("low"))
        cl = c.get("c", c.get("close"))
        v = c.get("v", c.get("tick_volume", c.get("volume", 0)))

        if t is None or o is None or h is None or l is None or cl is None:
            continue

        candles.append(
            {
                "t": int(t),
                "o": float(o),
                "h": float(h),
                "l": float(l),
                "c": float(cl),
                "v": int(v) if v is not None else 0,
            }
        )

    return {"candles": candles, "last_error": last_error}
