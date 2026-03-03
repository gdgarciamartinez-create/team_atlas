# src/atlas/core/safe_imports.py
from __future__ import annotations
from typing import Any, Callable, Dict

def safe_get_alerts_snapshot() -> Callable[..., Dict[str, Any]]:
    """
    Devuelve la función real get_alerts_snapshot si existe.
    Si no existe, devuelve un stub para que el server NO se caiga.
    """
    try:
        from atlas.core.alerts_state import get_alerts_snapshot  # type: ignore
        return get_alerts_snapshot
    except Exception as e:
        def _stub(limit: int = 50) -> Dict[str, Any]:
            return {
                "count": 0,
                "items": [],
                "error": f"ALERTS_STUB_ACTIVE: {type(e).__name__}: {e}",
            }
        return _stub
