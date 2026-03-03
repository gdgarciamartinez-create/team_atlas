from __future__ import annotations

from typing import Any, Dict

# Isla SCALPING M1: vive sola, no mezcla con M5.

def build_scalping_m1_snapshot() -> Dict[str, Any]:
    """
    Construye snapshot de la isla SCALPING_M1 usando el core real:
    atlas.bot.worlds.scalping_world.build_scalping_world(symbol, tf, ...)
    """
    # Ajustá el símbolo default si querés (o si lo trae tu feed)
    symbol = "XAUUSDz"
    tf = "M1"

    from atlas.bot.worlds.scalping_world import build_scalping_world  # type: ignore

    payload = build_scalping_world(symbol=symbol, tf=tf)

    # Normalización para ATLAS_IA
    payload["world"] = "ATLAS_IA"
    payload["atlas_mode"] = "SCALPING_M1"
    return payload