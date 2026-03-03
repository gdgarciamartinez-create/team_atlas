# src/atlas/bot/worlds/prese_world.py
from __future__ import annotations

from typing import Any, Dict, List


def build_prese_world(symbol: str, tf: str, candles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Mundo PRESESIÓN (pre NY).
    Placeholder: devuelve WAIT o ZONA si detecta rango apretado.
    """
    if not isinstance(candles, list) or len(candles) < 80:
        return {"state": "WAIT", "message": "PRE: sin suficientes velas"}

    # Rango simple en últimas 30 velas
    last30 = candles[-30:]
    try:
        hi = max(float(x["h"]) for x in last30)
        lo = min(float(x["l"]) for x in last30)
    except Exception:
        return {"state": "WAIT", "message": "PRE: formato de vela inválido"}

    rng = hi - lo

    # Umbral simple (lo ajustamos después). Si rango comprimido => ZONA
    if rng < 1.2:
        mid = (hi + lo) / 2.0
        return {
            "state": "ZONA",
            "side": None,
            "message": f"PRE: compresión detectada (rango={rng:.2f})",
            "zone": mid,
            "entry": None,
            "sl": None,
            "tp": None,
            "tp1": None,
        }

    return {"state": "WAIT", "message": f"PRE: rango amplio (rango={rng:.2f})"}