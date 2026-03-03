# src/atlas/api/feed.py

from __future__ import annotations

from typing import Any, Dict, List, Optional

from atlas.api.routes.mt5_provider import fetch_mt5_candles


def get_candles_payload(*, world: str, symbol: str, tf: str, count: int = 220) -> Dict[str, Any]:
    """
    Contrato:
    - Siempre retorna un dict con ok/world/symbol/tf/ts_ms/candles/source
    - Si MT5 falla: candles=[], source="mt5_error_fallback", error="..."
    - Nunca revienta el backend.
    """
    w = (world or "").strip()
    s = (symbol or "").strip()
    t = (tf or "").strip().upper()
    c = int(count or 220)

    res = fetch_mt5_candles(symbol=s, tf=t, count=c)

    if res.ok and res.candles:
        # Normal
        # ts_ms lo sacamos de la última vela (t en ms)
        ts_ms = int(res.candles[-1]["t"])
        return {
            "ok": True,
            "source": "mt5",
            "world": w,
            "symbol": s,
            "tf": t,
            "ts_ms": ts_ms,
            "candles": res.candles,
        }

    # Fallback con error claro
    return {
        "ok": True,
        "source": "mt5_error_fallback",
        "world": w,
        "symbol": s,
        "tf": t,
        "ts_ms": 0,
        "candles": [],
        "error": res.error or "UNKNOWN_MT5_ERROR",
    }