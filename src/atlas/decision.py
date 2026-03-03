# src/atlas/bot/decision.py
from __future__ import annotations
from typing import Any, Dict

# Modo laboratorio: nunca ejecuta, solo “permite avisar”.
def can_emit_trade_alert(*args: Any, **kwargs: Any) -> bool:
    return True

def mark_trade_alert(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    # Placeholder: después lo conectamos a logs/historial
    return {"ok": True}
