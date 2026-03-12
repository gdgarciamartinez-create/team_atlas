# src/atlas/engine.py
from __future__ import annotations

from typing import Any, Dict, List, Optional

# Import "seguro": si algo falta, no cae el server
try:
    from atlas.simulation import calculate_poi  # type: ignore
except Exception:
    calculate_poi = None  # type: ignore


class Engine:
    """
    Engine base "blindado": NO debe romper el backend por imports.
    Si tu proyecto tiene Engines específicos, esto sirve como base estable.
    """

    def __init__(self) -> None:
        pass

    def compute_poi(self, candles: List[Dict[str, Any]], lookback: int = 80) -> Dict[str, Any]:
        if calculate_poi is None:
            return {
                "ok": False,
                "reason": "calculate_poi_missing",
                "poi": 0.0,
                "hi": 0.0,
                "lo": 0.0,
                "last": 0.0,
                "lookback": int(lookback),
            }
        try:
            return calculate_poi(candles, lookback=lookback)
        except Exception as e:
            return {
                "ok": False,
                "reason": f"calculate_poi_error:{e}",
                "poi": 0.0,
                "hi": 0.0,
                "lo": 0.0,
                "last": 0.0,
                "lookback": int(lookback),
            }