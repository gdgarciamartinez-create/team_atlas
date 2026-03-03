# src/atlas/core/market_snapshot.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import time
import random


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fake_candles(symbol: str, tf: str, count: int) -> Dict[str, Any]:
    # Fake estable para UI: OHLC + timestamp unix (segundos)
    # No depende de MT5, siempre responde.
    base = 5000.0 if "XAU" in symbol.upper() else 20000.0
    t0 = int(time.time()) - (count * 60)

    candles: List[Dict[str, Any]] = []
    last = base

    for i in range(count):
        ts = t0 + i * 60
        o = last
        c = o + random.uniform(-2.0, 2.0)
        h = max(o, c) + random.uniform(0.0, 1.2)
        l = min(o, c) - random.uniform(0.0, 1.2)
        candles.append(
            {"time": ts, "open": o, "high": h, "low": l, "close": c}
        )
        last = c

    return {
        "ok": True,
        "source": "FAKE",
        "symbol_resolved": symbol,
        "tf": tf,
        "count": count,
        "candles": candles,
        "last_error": None,
    }


def get_market_snapshot(symbol: str, tf: str, count: int) -> Dict[str, Any]:
    """
    Fuente única de velas.
    - Si MT5 está disponible -> usar MT5
    - Si falla -> fallback fake (para no romper UI ni motor)
    """
    try:
        # IMPORT SOLO HACIA CORE (si tu mt5_engine está en core, ok)
        from atlas.core.mt5_engine import get_candles as mt5_get_candles  # type: ignore

        res = mt5_get_candles(symbol, tf, count)

        # Normalizamos forma mínima esperada
        if isinstance(res, dict) and res.get("ok") and res.get("candles") is not None:
            res.setdefault("source", "MT5")
            res.setdefault("symbol_resolved", symbol)
            res.setdefault("tf", tf)
            res.setdefault("count", count)
            return res

        # Si MT5 responde mal o vacío, no matamos el sistema
        return _fake_candles(symbol, tf, count)

    except Exception as e:
        # Cualquier excepción -> fallback fake
        fake = _fake_candles(symbol, tf, count)
        fake["last_error"] = f"MT5_FALLBACK: {e}"
        return fake
