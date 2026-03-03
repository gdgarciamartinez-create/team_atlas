# src/atlas/bot/decision.py
from __future__ import annotations

from typing import Any, Dict, Optional
import time

# Memoria simple por símbolo para evitar spam en laboratorio
_LAST_ALERT_TS: Dict[str, int] = {}


def can_emit_trade_alert(symbol: str, cooldown_sec: int = 60) -> bool:
    """
    LAB: permite emitir alerta si pasó cooldown_sec desde la última.
    """
    now = int(time.time())
    last = _LAST_ALERT_TS.get(symbol, 0)
    return (now - last) >= cooldown_sec


def mark_trade_alert(symbol: str) -> None:
    """
    LAB: marca el timestamp de la última alerta emitida.
    """
    _LAST_ALERT_TS[symbol] = int(time.time())
