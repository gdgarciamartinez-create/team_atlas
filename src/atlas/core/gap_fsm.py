# src/atlas/core/gap_fsm.py
from __future__ import annotations
from typing import List, Tuple, Dict, Optional
import time

from atlas.api.data_source import Candle
from atlas.bot.state import BOT_STATE

IDLE = "IDLE"
EXAGERACION = "EXAGERACION"
FALLO_CONTINUIDAD = "FALLO_CONTINUIDAD"
RUPTURA = "RUPTURA"
RECUPERACION = "RECUPERACION"
ACEPTACION = "ACEPTACION"
TRADE_READY = "TRADE_READY"
CLOSED = "CLOSED"

def gap_step(candles: List[Candle]) -> Tuple[str, Dict[str, bool], str, Optional[float]]:
    gs = BOT_STATE.get("gap") or {}
    current_state = gs.get("state", IDLE)
    tp_gap = gs.get("tp_gap", None)
    direction = gs.get("direction", None)  # UP/DOWN (dirección de exageración)

    steps = {
        "exageracion": current_state != IDLE,
        "fallo_continuidad": current_state in [FALLO_CONTINUIDAD, RUPTURA, RECUPERACION, ACEPTACION, TRADE_READY, CLOSED],
        "ruptura": current_state in [RUPTURA, RECUPERACION, ACEPTACION, TRADE_READY, CLOSED],
        "recuperacion": current_state in [RECUPERACION, ACEPTACION, TRADE_READY, CLOSED],
        "aceptacion": current_state in [ACEPTACION, TRADE_READY, CLOSED],
    }

    if len(candles) < 25:
        return current_state, steps, "NO_CANDLES", tp_gap

    last_c = candles[-1]
    prev_c = candles[-2]

    body = abs(last_c.c - last_c.o)
    avg_body = sum(abs(c.c - c.o) for c in candles[-20:-1]) / 19.0

    next_state = current_state
    reason = f"GAP_WAIT_{current_state}"

    if current_state == IDLE:
        if body > avg_body * 3.0:
            next_state = EXAGERACION
            reason = "EXAGERACION_DETECTED"
            tp_gap = prev_c.o
            direction = "UP" if last_c.c > last_c.o else "DOWN"

    elif current_state == EXAGERACION:
        if direction == "UP" and last_c.h > prev_c.h:
            next_state = CLOSED
            reason = "GAP_DISCARDED_CONTINUITY_OK"
        elif direction == "DOWN" and last_c.l < prev_c.l:
            next_state = CLOSED
            reason = "GAP_DISCARDED_CONTINUITY_OK"
        else:
            if direction == "UP" and last_c.c < last_c.o:
                next_state = FALLO_CONTINUIDAD
                reason = "FALLO_CONTINUIDAD_CONFIRMED"
            elif direction == "DOWN" and last_c.c > last_c.o:
                next_state = FALLO_CONTINUIDAD
                reason = "FALLO_CONTINUIDAD_CONFIRMED"

    elif current_state == FALLO_CONTINUIDAD:
        if direction == "UP" and last_c.c < prev_c.l:
            next_state = RUPTURA
            reason = "RUPTURA_CONFIRMED"
        elif direction == "DOWN" and last_c.c > prev_c.h:
            next_state = RUPTURA
            reason = "RUPTURA_CONFIRMED"

    elif current_state == RUPTURA:
        if direction == "UP" and last_c.c > last_c.o:
            next_state = RECUPERACION
            reason = "RECUPERACION_CONFIRMED"
        elif direction == "DOWN" and last_c.c < last_c.o:
            next_state = RECUPERACION
            reason = "RECUPERACION_CONFIRMED"

    elif current_state == RECUPERACION:
        if direction == "UP" and last_c.c < prev_c.l:
            next_state = ACEPTACION
            reason = "ACEPTACION_CONFIRMED"
        elif direction == "DOWN" and last_c.c > prev_c.h:
            next_state = ACEPTACION
            reason = "ACEPTACION_CONFIRMED"

    if current_state == ACEPTACION:
        next_state = TRADE_READY
        reason = "RITUAL_COMPLETED"

    elif current_state == TRADE_READY:
        if tp_gap is not None:
            paid = False
            if direction == "UP" and last_c.l <= tp_gap:
                paid = True
            elif direction == "DOWN" and last_c.h >= tp_gap:
                paid = True

            if paid:
                next_state = CLOSED
                reason = "GAP_PAID_SCENARIO_CLOSED"
                BOT_STATE["scenario"]["closed"] = True
                BOT_STATE["scenario"]["reason"] = "PAID_PLUS_DEVELOPMENT"
                BOT_STATE["scenario"]["closed_ts"] = int(time.time())

    BOT_STATE["gap"] = {"state": next_state, "tp_gap": tp_gap, "direction": direction}

    steps = {
        "exageracion": next_state != IDLE,
        "fallo_continuidad": next_state in [FALLO_CONTINUIDAD, RUPTURA, RECUPERACION, ACEPTACION, TRADE_READY, CLOSED],
        "ruptura": next_state in [RUPTURA, RECUPERACION, ACEPTACION, TRADE_READY, CLOSED],
        "recuperacion": next_state in [RECUPERACION, ACEPTACION, TRADE_READY, CLOSED],
        "aceptacion": next_state in [ACEPTACION, TRADE_READY, CLOSED],
    }

    return next_state, steps, reason, tp_gap
