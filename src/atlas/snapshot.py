from __future__ import annotations

from typing import Optional
from enum import Enum

from fastapi import APIRouter, Query

from atlas.snapshot_core import build_snapshot

router = APIRouter()


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


@router.get("/snapshot")
def snapshot(
    world: World = Query(default=World.ATLAS_IA),
    atlas_mode: Optional[AtlasMode] = Query(default=AtlasMode.SCALPING_M5),
    symbol: str = Query(default="XAUUSDz"),
    tf: str = Query(default="M5"),
    count: int = Query(default=220, ge=50, le=2000),
):
    # ATLAS_IA usa atlas_mode, el resto lo ignora.
    mode = atlas_mode.value if world.value == "ATLAS_IA" and atlas_mode is not None else None
    return build_snapshot(
        world=world.value,
        atlas_mode=mode,
        symbol=symbol,
        tf=tf,
        count=count,
    )