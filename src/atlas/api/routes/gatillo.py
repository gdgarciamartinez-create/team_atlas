from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter
from pydantic import BaseModel

from atlas.bot.gatillo.engine import GatilloEngine

router = APIRouter(prefix="/gatillos", tags=["gatillos"])

# Engine singleton simple (igual que el resto de tu arquitectura)
_ENGINE: GatilloEngine | None = None


def gatillos_engine() -> GatilloEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = GatilloEngine()
    return _ENGINE


class PlanIn(BaseModel):
    side: str
    zone_low: float
    zone_high: float


@router.post("/plan")
def set_plan(inp: PlanIn) -> Dict[str, Any]:
    e = gatillos_engine()
    e.set_plan(side=inp.side.upper(), zone_low=inp.zone_low, zone_high=inp.zone_high)
    return {"ok": True, "plan": {"side": inp.side.upper(), "zone_low": inp.zone_low, "zone_high": inp.zone_high}}


@router.post("/reset")
def reset() -> Dict[str, Any]:
    e = gatillos_engine()
    e.reset()
    return {"ok": True}

@router.post("/reset")
def reset_gatillo():
    engine = gatillos_engine()
    engine.reset()
    return {"ok": True}
