from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# TEAM ATLAS - Simulation helpers
# ------------------------------------------------------------
# Este módulo existe para utilidades de simulación/cálculos
# que pueden ser usados por engine.py sin romper el backend.
#
# FIX CRÍTICO:
# - engine.py está importando calculate_poi
# - pero simulation.py NO lo tenía
# => Uvicorn muere al importar
# ============================================================


def _f(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _normalize_candles(candles: Any) -> List[Dict[str, Any]]:
    """
    Normaliza candles a: [{t,o,h,l,c,v}, ...]
    Acepta lista de dicts con llaves open/high/low/close o o/h/l/c.
    """
    if not isinstance(candles, list):
        return []

    out: List[Dict[str, Any]] = []
    for c in candles:
        if not isinstance(c, dict):
            continue
        t = c.get("t", c.get("time", 0))
        o = c.get("o", c.get("open", 0))
        h = c.get("h", c.get("high", 0))
        l = c.get("l", c.get("low", 0))
        cl = c.get("c", c.get("close", 0))
        v = c.get("v", c.get("tick_volume", c.get("volume", 0)))
        out.append(
            {
                "t": int(_f(t, 0)),
                "o": _f(o),
                "h": _f(h),
                "l": _f(l),
                "c": _f(cl),
                "v": _f(v),
            }
        )
    return out


@dataclass
class POIResult:
    """
    POI = Point of Interest (simple, estable, sin magia).
    Este resultado es intencionalmente minimalista:
    - hi/lo del tramo observado
    - mid (50%)
    - último close
    """
    hi: float
    lo: float
    mid: float
    last: float


def calculate_poi(
    candles: Any,
    *,
    lookback: int = 80,
) -> Dict[str, Any]:
    """
    calculate_poi (FIX de import)
    ------------------------------------------------------------
    Devuelve un POI simple y estable para no romper el engine.

    - No intenta "inventar" un método.
    - Solo calcula referencias de rango recientes para que
      el engine tenga algo consistente cuando lo llame.

    Returns dict:
      {
        "ok": True/False,
        "poi": <mid>,
        "hi": <hi>,
        "lo": <lo>,
        "last": <last>,
        "lookback": <lookback>
      }
    """
    c = _normalize_candles(candles)
    if len(c) < 5:
        return {
            "ok": False,
            "reason": "NOT_ENOUGH_CANDLES",
            "poi": 0.0,
            "hi": 0.0,
            "lo": 0.0,
            "last": 0.0,
            "lookback": lookback,
        }

    use = c[-max(5, int(lookback)) :]
    hi = max(_f(x.get("h"), 0.0) for x in use)
    lo = min(_f(x.get("l"), 0.0) for x in use)
    last = _f(use[-1].get("c"), 0.0)
    mid = (hi + lo) / 2.0

    r = POIResult(hi=hi, lo=lo, mid=mid, last=last)
    return {
        "ok": True,
        "poi": r.mid,
        "hi": r.hi,
        "lo": r.lo,
        "last": r.last,
        "lookback": lookback,
    }