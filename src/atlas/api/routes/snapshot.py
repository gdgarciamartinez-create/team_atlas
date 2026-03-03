from __future__ import annotations

from fastapi import APIRouter, Query
from typing import Optional

from atlas.snapshot_core import build_snapshot
from atlas.bot.bitacora.engine import process_snapshot_for_bitacora
from atlas.bot.bitacora.store import compute_stats_filtered

router = APIRouter()


@router.get("/snapshot")
def snapshot(
    world: str = Query("ATLAS_IA"),
    atlas_mode: str = Query("SCALPING_M5"),
    symbol: str = Query("XAUUSDz"),
    tf: str = Query("M5"),
    count: int = Query(220, ge=50, le=2000),
    bitacora_limit: int = Query(500, ge=50, le=5000),
):
    snap = build_snapshot(
        world=world,
        atlas_mode=atlas_mode,
        symbol=symbol,
        tf=tf,
        count=count,
    )

    # 1) procesa bitácora (abre/cierra si corresponde)
    snap = process_snapshot_for_bitacora(snap)

    # 2) inyecta stats (C: world+symbol+tf) dentro del snapshot
    try:
        stats = compute_stats_filtered(world=world, symbol=symbol, tf=tf, limit=bitacora_limit)
    except Exception:
        stats = {
            "scope": {"world": str(world).upper(), "symbol": str(symbol), "tf": str(tf).upper()},
            "error": "stats_failed",
        }

    snap["bitacora"] = {
        "stats": stats,
    }

    return snap