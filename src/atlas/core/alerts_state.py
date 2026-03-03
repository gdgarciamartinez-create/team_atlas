# src/atlas/core/alerts_state.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
import time

# Buffer simple de alertas (lab). No rompe imports.
_ALERTS: List[Dict[str, Any]] = []
_WORLD: str = "GENERAL"  # GENERAL | GAP | PRESESION


def set_world(world: str) -> None:
    """Usado por /api/alerts/world y snapshot. No afecta doctrina."""
    global _WORLD
    _WORLD = (world or "GENERAL").strip().upper()


def get_world() -> str:
    return _WORLD


def push_alert(kind: str, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
    """Agrega una alerta al buffer (máx 200)."""
    _ALERTS.append(
        {
            "ts": int(time.time()),
            "kind": str(kind),
            "message": str(message),
            "extra": extra or {},
            "world": _WORLD,
        }
    )
    if len(_ALERTS) > 200:
        del _ALERTS[:50]


def clear_alerts() -> None:
    _ALERTS.clear()


def get_alerts_snapshot(limit: int = 50) -> Dict[str, Any]:
    """Lo que consume /api/alerts y /api/snapshot. Siempre existe."""
    lim = max(0, min(int(limit), 200))
    items = _ALERTS[-lim:] if lim > 0 else list(_ALERTS)
    return {"count": len(_ALERTS), "items": items, "world": _WORLD}
