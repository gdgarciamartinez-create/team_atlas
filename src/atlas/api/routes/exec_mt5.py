from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from atlas.api.routes.exec import arm_state, last_exec_state
from atlas.data.mt5_connector import MT5Connector

router = APIRouter()
connector = MT5Connector()
ARMED = False

class ExecBody(BaseModel):
    symbol: str
    side: str
    lot: float
    sl: float
    tp: Optional[float] = None

@router.post("/exec/arm")
def arm():
    global ARMED
    ARMED = True
    return {"armed": True}

@router.post("/exec/disarm")
def disarm():
    global ARMED
    ARMED = False
    return {"armed": False}

@router.post("/exec/place")
def place(body: ExecBody):
    if not ARMED:
        return {"ok": False, "error": "NOT_ARMED"}
    return connector.place_market(
        symbol=body.symbol,
        side=body.side,
        lots=body.lot,
        sl=body.sl,
        tp=body.tp
    )