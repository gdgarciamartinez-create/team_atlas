from __future__ import annotations
from typing import Any, Dict


def atlas_ia_snapshot(
    mode: str,
    symbol: str | None = None,
    tf: str | None = None,
    count: int = 200,
) -> Dict[str, Any]:

    mode = (mode or "").upper().strip()

    if mode == "SCALPING_M1":
        from atlas.bot.atlas_ia_m1.engine import build_snapshot

        payload = build_snapshot(symbol=symbol, tf=tf, count=count)
        payload["world"] = "ATLAS_IA"
        payload["atlas_mode"] = "SCALPING_M1"
        return payload

    if mode == "SCALPING_M5":
        from atlas.bot.atlas_ia_m5.engine import build_snapshot

        payload = build_snapshot(symbol=symbol, tf=tf, count=count)
        payload["world"] = "ATLAS_IA"
        payload["atlas_mode"] = "SCALPING_M5"
        return payload

    if mode == "FOREX":
        from atlas.bot.atlas_ia.engine import build_snapshot

        payload = build_snapshot(symbol=symbol, tf=tf, count=count)
        payload["world"] = "ATLAS_IA"
        payload["atlas_mode"] = "FOREX"
        return payload

    return {
        "world": "ATLAS_IA",
        "atlas_mode": mode,
        "analysis": {"status": "NO_TRADE", "reason": "UNKNOWN_MODE"},
        "ui": {"rows": [], "meta": {"note": "Unknown mode"}},
    }