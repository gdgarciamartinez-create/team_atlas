from __future__ import annotations

from fastapi import APIRouter
from typing import Any, Dict, Optional

from atlas.worlds_tf import get_world_tf, WORLDS
from atlas.fib_opt_store import FibOptStore

router = APIRouter(prefix="/world_config", tags=["world_config"])

FIB = FibOptStore()


@router.get("")
def get_config(
    world: str = "ATLAS_IA",
    atlas_mode: Optional[str] = None,
    symbol: Optional[str] = None,
) -> Dict[str, Any]:
    resolved = get_world_tf(world, atlas_mode=atlas_mode, symbol=symbol)
    fib = FIB.get(symbol or "") if symbol else None

    return {
        "ok": True,
        "request": {"world": world, "atlas_mode": atlas_mode, "symbol": symbol},
        "worlds": {k: {"analysis_tfs": v.analysis_tfs, "trigger_tfs": v.trigger_tfs, "note": v.note} for k, v in WORLDS.items()},
        "resolved": {"world": resolved.world, "analysis_tfs": resolved.analysis_tfs, "trigger_tfs": resolved.trigger_tfs, "note": resolved.note},
        "fib_opt": fib.to_dict() if fib else None,
    }


@router.get("/fib_opt/all")
def fib_opt_all() -> Dict[str, Any]:
    return {"ok": True, "items": FIB.all()}