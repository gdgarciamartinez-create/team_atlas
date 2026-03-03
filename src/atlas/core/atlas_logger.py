# src/atlas/core/atlas_logger.py
from __future__ import annotations
from typing import Dict, Any, Optional
from atlas.main_state import AUDIT


def log_event(
    kind: str,
    world: str,
    symbol: str,
    tf: str,
    action: str,
    reason: str,
    checklist: Optional[Dict] = None,
    extra: Optional[Dict] = None,
):
    """
    Wrapper normalizado para el AuditLog.
    """
    payload = {
        "action": action,
        "reason": reason,
        "checklist": checklist or {},
        "extra": extra or {},
    }
    AUDIT.write(kind=kind.upper(), payload=payload, symbol=symbol, window=f"{world}|{tf}")