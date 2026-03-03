from __future__ import annotations

from typing import Any, Dict

# Isla SCALPING M5: vive sola, no mezcla con M1.

def build_scalping_m5_snapshot() -> Dict[str, Any]:
    """
    Construye snapshot de la isla SCALPING_M5 usando el core real:
    atlas.bot.worlds.scalping_world.build_scalping_world(symbol, tf, ...)
    """
    symbol = "XAUUSDz"
    tf = "M5"

    from atlas.bot.worlds.scalping_world import build_scalping_world  # type: ignore

    payload = build_scalping_world(symbol=symbol, tf=tf)

    # Normalización para ATLAS_IA
    payload["world"] = "ATLAS_IA"
    payload["atlas_mode"] = "SCALPING_M5"
    return payload