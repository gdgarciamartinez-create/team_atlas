# src/atlas/api/routes/motor_doctrinal.py
from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel
import time
from typing import Dict, Any

from atlas.api.data_source_real import YahooDataSourceReal
from atlas.core.atlas_types import POI, Decision
from atlas.core import fibo_utils
from atlas.core.decision_engine import decide_from_poi
from atlas.core.doctrine_guard import assert_no_079, DoctrinalError
from atlas.core.gap_fsm import gap_step, TRADE_READY
from atlas.core.atlas_logger import log_event
from atlas.bot.state import BOT_STATE
from atlas.bot.feed_control import feed_control

router = APIRouter()

YAHOO_MAP = {"EURUSD": "EURUSD=X", "XAUUSD": "GC=F"}
DATA_SOURCE = YahooDataSourceReal(symbol_map=YAHOO_MAP, interval="1m", period="1d")


class EvalBody(BaseModel):
    world: str
    symbol: str
    tf: str
    balance: float = 10000.0
    meta: Dict[str, Any] | None = None


def evaluate(body: EvalBody) -> Dict[str, Any]:
    candles = DATA_SOURCE.fetch(body.symbol)
    poi: POI | None = None
    gap_info = {}
    extra_log_info = {}

    if body.world == "GAP" and body.symbol == "XAUUSD":
        state, steps, reason, tp_gap = gap_step(candles)
        gap_info = {"state": state, "steps": steps, "reason": reason}
        extra_log_info["gap_fsm"] = gap_info
        if state == TRADE_READY and tp_gap is not None:
            last_high = max(c.h for c in candles[-5:])
            last_low = min(c.l for c in candles[-5:])
            curr_price = candles[-1].c
            trade_dir = "DOWN" if tp_gap < curr_price else "UP"
            
            poi = POI(
                low=last_low,
                high=last_high,
                direction=trade_dir,
                meta={"strategy": "GAP_FADE", "tp_override": tp_gap},
            )
    elif len(candles) > 20:
        direction = "UP" if candles[-1].c > candles[-1].o else "DOWN"
        recent_candles = candles[-20:]
        high = max(c.h for c in recent_candles)
        low = min(c.l for c in recent_candles)
        z_low, z_high = fibo_utils.fibo_0_786_zone(high, low, direction, pad=(high - low) * 0.02)
        poi = POI(low=z_low, high=z_high, direction=direction, meta={"strategy": "FIBO_0.786"})

    if poi:
        decision = decide_from_poi(body.world, body.symbol, body.tf, candles, poi, body.balance)
        if poi.meta and "tp_override" in poi.meta:
            decision["tp"] = poi.meta["tp_override"]
    else:
        decision = {
            "action": "NO_TRADE",
            "reason": "NO_POI_GENERATED",
            "confidence": 0.0,
            "checklist": {"contexto": "FAIL: No se pudo generar POI"},
        }

    log_event(
        kind="DECISION",
        world=body.world,
        symbol=body.symbol,
        tf=body.tf,
        action=decision["action"],
        reason=decision["reason"],
        checklist=decision.get("checklist"),
        extra={**extra_log_info, "poi": poi.__dict__ if poi else None},
    )

    snapshot = {
        "decision": decision,
        "scenario": BOT_STATE.get("scenario"),
        "gap_info": gap_info if body.world == "GAP" else None,
        "last_eval_ts": int(time.time()),
        "last_error": None,
    }

    try:
        assert_no_079(snapshot, body.world)
    except DoctrinalError:
        snapshot["last_error"] = "DOCTRINAL_GUARD_079"
        snapshot["decision"] = {
            "action": "NO_TRADE",
            "reason": "DOCTRINAL_GUARD_079",
            "confidence": 0.0,
            "checklist": {"doctrinal_guard": "FAIL"},
        }

    return snapshot


@router.post("/motor/evaluate", tags=["Doctrina"])
def evaluate_route(body: EvalBody):
    # ---- ATLAS FEED CONTROL GATE (BEGIN) ----
    if feed_control.mode != "play":
        cached = feed_control.get_last_snapshot()
        if cached is not None:
            return cached
    # (si no hay cached, cae al flujo normal para construir un snapshot base)
    # ---- ATLAS FEED CONTROL GATE (END) ----

    # flujo normal actual (construye snap)
    snapshot = evaluate(body)

    # si estamos en play, contar tick
    if feed_control.mode == "play":
        feed_control.on_tick()

    # cachear y devolver
    feed_control.set_last_snapshot(snapshot)
    return snapshot