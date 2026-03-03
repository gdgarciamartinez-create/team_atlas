# src/atlas/core/decision_engine.py
from __future__ import annotations
from typing import List, Dict, Any
import time

from atlas.core.atlas_types import POI, Decision
from atlas.api.data_source import Candle
from atlas.core import fibo_utils
from atlas.bot.state import BOT_STATE, set_phase
from atlas.core.alerts_state import push_alert


def _detect_scenario_closure(candles: List[Candle]) -> bool:
    if len(candles) < 30:
        return False
    last_30 = candles[-30:]
    ranges = [(c.h - c.l) for c in last_30]
    avg = sum(ranges[:15]) / 15.0 if sum(ranges[:15]) > 0 else 1.0

    idx = -1
    for i in range(18, 30):
        if ranges[i] > avg * 2.2:
            idx = i
            break
    if idx == -1:
        return False

    ex = last_30[idx]
    direction = "UP" if ex.c > ex.o else "DOWN"
    after = last_30[idx + 1 :]
    if len(after) < 4:
        return False

    if direction == "UP":
        if any(c.h > ex.h for c in after):
            return False
        return after[-1].c < ex.l
    else:
        if any(c.l < ex.l for c in after):
            return False
        return after[-1].c > ex.h

def decide_from_poi(
    world: str,
    symbol: str,
    tf: str,
    candles: List[Candle],
    poi: POI,
    balance: float = 10000.0,
) -> Decision:
    if BOT_STATE.get("scenario", {}).get("closed", False):
        set_phase("IDLE", "NO_TRADE", "SCENARIO_CLOSED")
        return {"action": "NO_TRADE", "reason": "SCENARIO_CLOSED", "confidence": 0.0, "checklist": {"escenario_abierto": False}}

    if _detect_scenario_closure(candles):
        BOT_STATE["scenario"]["closed"] = True
        BOT_STATE["scenario"]["reason"] = "PAID_PLUS_DEVELOPMENT"
        BOT_STATE["scenario"]["closed_ts"] = int(time.time())
        set_phase("IDLE", "NO_TRADE", "SCENARIO_CLOSED")
        return {"action": "NO_TRADE", "reason": "SCENARIO_CLOSED", "confidence": 0.0, "checklist": {"escenario_abierto": False}}

    checklist: Dict[str, bool] = {
        "contexto": False,
        "fibo_786": False,
        "zona": False,
        "timing": False,
        "invalidacion_2_cierres": True,
        "escenario_abierto": True,
    }

    if len(candles) < 20:
        set_phase("IDLE", "NO_TRADE", "NO_CANDLES")
        return {"action": "NO_TRADE", "reason": "NO_CANDLES", "confidence": 0.0, "checklist": checklist}

    checklist["contexto"] = True
    checklist["fibo_786"] = True

    zone = (poi.low, poi.high)
    highs = [c.h for c in candles]
    lows = [c.l for c in candles]
    prices_to_check = highs if poi.direction == "DOWN" else lows

    if not fibo_utils.touched_zone_last(prices_to_check, z_low=zone[0], z_high=zone[1], lookback=3):
        checklist["zona"] = False
        set_phase("OBSERVANDO", "WAIT")
        return {"action": "WAIT", "reason": "WAIT_TOUCH_0_786", "confidence": 0.3, "checklist": checklist}
    checklist["zona"] = True

    closes = [c.c for c in candles]
    if fibo_utils.closes_outside_zone_against(closes, z_low=zone[0], z_high=zone[1], direction=poi.direction, consecutive=2):
        checklist["invalidacion_2_cierres"] = False
        set_phase("IDLE", "NO_TRADE", "INVALIDATED_BY_TWO_CLOSES")
        push_alert("NO_TRADE", f"{symbol} {tf}: INVALIDATED_BY_TWO_CLOSES", {"world": world})
        return {"action": "NO_TRADE", "reason": "INVALIDATED_BY_TWO_CLOSES", "confidence": 0.0, "checklist": checklist}

    last = candles[-1]
    confirmed = (poi.direction == "UP" and last.c > last.o) or (poi.direction == "DOWN" and last.c < last.o)
    if not confirmed:
        checklist["timing"] = False
        set_phase("OBSERVANDO", "WAIT")
        return {"action": "WAIT", "reason": "WAIT_TIMING_CONFIRM", "confidence": 0.6, "checklist": checklist}
    checklist["timing"] = True

    side = "BUY" if poi.direction == "UP" else "SELL"
    entry = float(last.c)

    if side == "BUY":
        sl = float(poi.low)
        tp = entry + (entry - sl) * 2.5
    else:
        sl = float(poi.high)
        tp = entry - (sl - entry) * 2.5

    if (side == "BUY" and entry <= sl) or (side == "SELL" and entry >= sl):
        set_phase("IDLE", "NO_TRADE", "BAD_RISK_GEOMETRY")
        return {"action": "NO_TRADE", "reason": "BAD_RISK_GEOMETRY", "confidence": 0.0, "checklist": checklist}

    set_phase("ALERTADO", "TRADE")
    push_alert("TRADE", f"{symbol} {tf}: {side} señal", {"entry": entry, "sl": sl, "tp": float(tp), "world": world})
    return {
        "action": "TRADE",
        "side": side,
        "entry": entry,
        "sl": sl,
        "tp": float(tp),
        "reason": "TRADE_OK",
        "confidence": 1.0,
        "checklist": checklist,
        "tags": ["lab_signal"],
    }