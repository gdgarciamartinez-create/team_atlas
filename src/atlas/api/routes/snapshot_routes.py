from __future__ import annotations

from typing import Any, Dict, Optional
from enum import Enum

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter()

# ============================================================
# ENUMS
# ============================================================

class World(str, Enum):
    GAP = "GAP"
    PRESESION = "PRESESION"
    GATILLO = "GATILLO"
    ATLAS_IA = "ATLAS_IA"
    BITACORA = "BITACORA"


class AtlasMode(str, Enum):
    SCALPING_M1 = "SCALPING_M1"
    SCALPING_M5 = "SCALPING_M5"
    FOREX = "FOREX"


# ============================================================
# RESPONSE MODEL (flexible para UI)
# ============================================================

class SnapshotResponse(BaseModel):
    ok: bool = True
    world: str
    atlas_mode: Optional[str] = None
    payload: Dict[str, Any]


def _empty_payload(world: str, atlas_mode: Optional[str] = None, reason: str = "NO_DATA") -> Dict[str, Any]:
    return {
        "world": world,
        "atlas_mode": atlas_mode,
        "analysis": {"status": "NO_TRADE", "reason": reason},
        "ui": {"rows": [], "meta": {"note": "Empty snapshot"}},
    }


def _get_world_snapshot(world: World, atlas_mode: Optional[AtlasMode]) -> Dict[str, Any]:
    """
    Dispatcher profesional:
    - GAP / PRESESION / GATILLO / BITACORA: snapshots aislados
    - ATLAS_IA: exige atlas_mode y llama a tus islas
    """
    try:
        if world == World.ATLAS_IA:
            if atlas_mode is None:
                return _empty_payload(world.value, None, reason="MISSING_ATLAS_MODE")

            # ✅ usa TU función final (la que pegaste)
            from atlas.bot.islands.atlas_ia_world import atlas_ia_snapshot  # type: ignore
            return atlas_ia_snapshot(atlas_mode.value)

        if world == World.GAP:
            from atlas.bot.worlds.gap_world import build_gap_snapshot  # type: ignore
            return build_gap_snapshot()

        if world == World.PRESESION:
            from atlas.bot.worlds.presesion_world import build_presesion_snapshot  # type: ignore
            return build_presesion_snapshot()

        if world == World.GATILLO:
            from atlas.bot.worlds.gatillo_world import build_gatillo_snapshot  # type: ignore
            return build_gatillo_snapshot()

        if world == World.BITACORA:
            from atlas.bot.worlds.bitacora_world import build_bitacora_snapshot  # type: ignore
            return build_bitacora_snapshot()

        return _empty_payload(world.value, atlas_mode.value if atlas_mode else None, reason="UNKNOWN_WORLD")

    except Exception as e:
        return {
            "world": world.value,
            "atlas_mode": atlas_mode.value if atlas_mode else None,
            "analysis": {"status": "NO_TRADE", "reason": "EXCEPTION", "detail": str(e)[:300]},
            "ui": {"rows": [], "meta": {"note": "Exception in world snapshot builder"}},
        }


@router.get("/snapshot", response_model=SnapshotResponse)
def snapshot(
    world: World = Query(default=World.ATLAS_IA),
    atlas_mode: Optional[AtlasMode] = Query(default=AtlasMode.SCALPING_M1),
) -> SnapshotResponse:
    payload = _get_world_snapshot(world, atlas_mode if world == World.ATLAS_IA else None)
    return SnapshotResponse(
        ok=True,
        world=world.value,
        atlas_mode=(atlas_mode.value if world == World.ATLAS_IA else None),
        payload=payload,
    )