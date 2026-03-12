from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from atlas.state_store import (
    set_wait,
    set_wait_gatillo,
    set_signal,
    snapshot_plan,
)

router = APIRouter()


# -----------------------------
# Models (requests)
# -----------------------------
class PlanKey(BaseModel):
    world: str = Field(default="ATLAS_IA")
    atlas_mode: str = Field(default="SCALPING")
    symbol: str = Field(default="XAUUSDz")
    tf: str = Field(default="M5")


class SetWaitReq(PlanKey):
    reason: Optional[str] = None


class SetWaitGatilloReq(PlanKey):
    bias: Optional[str] = None
    zone: Optional[Dict[str, Any]] = None
    idea: Optional[str] = None


class SetSignalReq(PlanKey):
    entry: float
    sl: float
    tp: float
    tp1: Optional[float] = None


# -----------------------------
# Routes
# -----------------------------
@router.get("/plan")
def get_plan(
    world: str = "ATLAS_IA",
    atlas_mode: str = "SCALPING",
    symbol: str = "XAUUSDz",
    tf: str = "M5",
):
    """
    Devuelve el plan congelado actual (memoria backend).
    """
    return {
        "ok": True,
        "plan": snapshot_plan(world, atlas_mode, symbol, tf),
    }


@router.post("/plan/set_wait")
def api_set_wait(req: SetWaitReq):
    """
    Resetea a WAIT (borra plan y ejecución congelada).
    """
    p = set_wait(req.world, req.atlas_mode, req.symbol, req.tf, reason=req.reason)
    return {"ok": True, "plan": p.to_dict()}


@router.post("/plan/set_wait_gatillo")
def api_set_wait_gatillo(req: SetWaitGatilloReq):
    """
    Congela el PLAN (zona/idea/sesgo) sin entry/SL/TP todavía.
    """
    p = set_wait_gatillo(
        req.world,
        req.atlas_mode,
        req.symbol,
        req.tf,
        bias=req.bias,
        zone=req.zone,
        idea=req.idea,
    )
    return {"ok": True, "plan": p.to_dict()}


@router.post("/plan/set_signal")
def api_set_signal(req: SetSignalReq):
    """
    Congela la SEÑAL (entry/SL/TP) y queda fija hasta invalidación.
    """
    p = set_signal(
        req.world,
        req.atlas_mode,
        req.symbol,
        req.tf,
        entry=req.entry,
        sl=req.sl,
        tp=req.tp,
        tp1=req.tp1,
    )
    return {"ok": True, "plan": p.to_dict()}