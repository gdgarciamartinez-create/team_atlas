from __future__ import annotations

from typing import Any, Dict


def atlas_ia_snapshot(mode: str) -> Dict[str, Any]:
    """
    Motor central de ATLAS_IA.
    No usa islands.
    Despacha directamente a las islas actuales dentro de bot/worlds.
    """

    mode = (mode or "").upper().strip()

    try:
        # ----------------------------
        # SCALPING M1
        # ----------------------------
        if mode == "SCALPING_M1":
            from atlas.bot.worlds.scalping_world import (  # type: ignore
                build_scalping_snapshot_m1,
            )

            payload = build_scalping_snapshot_m1()
            payload["world"] = "ATLAS_IA"
            payload["atlas_mode"] = "SCALPING_M1"
            return payload

        # ----------------------------
        # SCALPING M5
        # ----------------------------
        if mode == "SCALPING_M5":
            from atlas.bot.worlds.scalping_world import (  # type: ignore
                build_scalping_snapshot_m5,
            )

            payload = build_scalping_snapshot_m5()
            payload["world"] = "ATLAS_IA"
            payload["atlas_mode"] = "SCALPING_M5"
            return payload

        # ----------------------------
        # FOREX
        # ----------------------------
        if mode == "FOREX":
            from atlas.bot.worlds.forex_world import (  # type: ignore
                build_forex_world_snapshot,
            )

            payload = build_forex_world_snapshot()
            payload["world"] = "ATLAS_IA"
            payload["atlas_mode"] = "FOREX"
            return payload

        # ----------------------------
        # MODE DESCONOCIDO
        # ----------------------------
        return {
            "world": "ATLAS_IA",
            "atlas_mode": mode,
            "analysis": {
                "status": "NO_TRADE",
                "reason": "UNKNOWN_MODE",
            },
            "ui": {
                "rows": [],
                "meta": {"note": "Unknown ATLAS_IA mode"},
            },
        }

    except Exception as e:
        return {
            "world": "ATLAS_IA",
            "atlas_mode": mode,
            "analysis": {
                "status": "NO_TRADE",
                "reason": "EXCEPTION",
                "detail": str(e)[:300],
            },
            "ui": {
                "rows": [],
                "meta": {"note": "Exception inside atlas_ia_engine"},
            },
        }