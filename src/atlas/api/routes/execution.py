from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import time

import MetaTrader5 as mt5

router = APIRouter()

# Estado simple de armado (en memoria)
ARMED: Dict[str, Any] = {"armed": False, "last": None}

class ExecBody(BaseModel):
    symbol: str
    side: str          # BUY | SELL
    lot: float
    sl: float
    tp: Optional[float] = None
    deviation: int = 30

def _ensure_mt5():
    if not mt5.initialize():
        code, msg = mt5.last_error()
        raise HTTPException(status_code=500, detail={"mt5_init": False, "error": {"code": code, "msg": msg}})

@router.get("/armed")
def get_armed():
    return {"armed": bool(ARMED["armed"]), "last": ARMED["last"]}

@router.post("/arm")
def arm():
    ARMED["armed"] = True
    ARMED["last"] = {"ts": int(time.time()), "action": "arm"}
    return {"ok": True, "armed": True}

@router.post("/disarm")
def disarm():
    ARMED["armed"] = False
    ARMED["last"] = {"ts": int(time.time()), "action": "disarm"}
    return {"ok": True, "armed": False}

@router.post("/place")
def place(body: ExecBody):
    if not ARMED["armed"]:
        return {"ok": False, "error": "NOT_ARMED"}

    side = body.side.upper().strip()
    if side not in ("BUY", "SELL"):
        return {"ok": False, "error": "side must be BUY|SELL"}

    _ensure_mt5()

    info = mt5.symbol_info(body.symbol)
    if info is None or not info.visible:
        if not mt5.symbol_select(body.symbol, True):
            return {"ok": False, "error": "SYMBOL_NOT_VISIBLE", "symbol": body.symbol}

    tick = mt5.symbol_info_tick(body.symbol)
    if tick is None:
        return {"ok": False, "error": "NO_TICK_DATA", "symbol": body.symbol}

    price = tick.ask if side == "BUY" else tick.bid
    order_type = mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": body.symbol,
        "volume": float(body.lot),
        "type": order_type,
        "price": float(price),
        "sl": float(body.sl),
        "tp": float(body.tp) if body.tp is not None else 0.0,
        "deviation": int(body.deviation),
        "magic": 260208,
        "comment": "ATLAS_EXEC",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }

    result = mt5.order_send(request)
    err = mt5.last_error()

    if result is None:
        return {"ok": False, "error": "ORDER_SEND_FAILED", "last_error": {"code": err[0], "msg": err[1]}}

    payload = {
        "ok": result.retcode == mt5.TRADE_RETCODE_DONE,
        "retcode": int(result.retcode),
        "comment": str(result.comment),
        "request_id": int(result.request_id),
        "order": int(result.order),
        "deal": int(result.deal),
        "price": float(price),
        "symbol": body.symbol,
        "side": side,
        "lot": float(body.lot),
    }

    if not payload["ok"]:
        payload["last_error"] = {"code": err[0], "msg": err[1]}

    ARMED["last"] = {"ts": int(time.time()), "action": "place", "payload": payload}
    return payload