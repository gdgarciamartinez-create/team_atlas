# src/atlas/bot/worlds/atlas_ia_world.py
from __future__ import annotations

from typing import Any, Dict

# ATLAS_IA es un contenedor de islas:
# - SCALPING_M1 (isla)
# - SCALPING_M5 (isla)
# - FOREX (isla)
#
# Regla: NO mezclar islas. Solo despachar.

def build_atlas_ia_snapshot(atlas_mode: str) -> Dict[str, Any]:
    """
    Devuelve el snapshot del mundo ATLAS_IA según la isla (atlas_mode).
    Espera:
      - "SCALPING_M1"
      - "SCALPING_M5"
      - "FOREX"
    """
    mode = (atlas_mode or "").upper().strip()

    # ---- SCALPING M1 (isla) ----
    if mode == "SCALPING_M1":
        from atlas.bot.worlds.atlas_ia_scalping_m1 import (  # type: ignore
            build_scalping_m1_snapshot,
        )
        return build_scalping_m1_snapshot()

    # ---- SCALPING M5 (isla) ----
    if mode == "SCALPING_M5":
        from atlas.bot.worlds.atlas_ia_scalping_m5 import (  # type: ignore
            build_scalping_m5_snapshot,
        )
        return build_scalping_m5_snapshot()

    # ---- FOREX (isla) ----
    if mode == "FOREX":
        from atlas.bot.worlds.atlas_ia_forex import (  # type: ignore
            build_forex_snapshot,
        )
        return build_forex_snapshot()

    # ---- Fallback seguro (nunca romper UI) ----
    return {
        "world": "ATLAS_IA",
        "atlas_mode": mode,
        "analysis": {
            "status": "NO_TRADE",
            "reason": "UNKNOWN_ATLAS_MODE",
            "detail": f"atlas_mode='{mode}' (expected: SCALPING_M1 | SCALPING_M5 | FOREX)",
        },
        "ui": {
            "rows": [],
            "meta": {"note": "Unknown atlas_mode"},
        },
    }