from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple, Literal
import time
from atlas.bot.state import BOT_STATE, set_phase

# ============================================================
# TEAM ATLAS — BLOQUE LÓGICO FINAL (CORE ENGINE)
# ============================================================

class DoctrinalError(Exception):
    pass

SENSITIVE_KEYS = {"entry", "sl", "tp", "zone", "level", "price", "swing", "fibo", "poi"}

# -----------------------------------------
# 6. DOCTRINA 0.79 (GUARDIÁN)
# -----------------------------------------
def assert_no_079(payload: Any, world: str) -> None:
    """
    Reglas:
    - 0.79 prohibido siempre como float.
    - EXCEPTO: world == PRESESION (como string en keys no sensibles).
    """
    _recursive_guard_079(payload, world)

def _is_forbidden_float(val: Any) -> bool:
    if isinstance(val, (float, int)):
        return abs(float(val) - 0.79) < 0.0005
    return False

def _recursive_guard_079(data: Any, world: str, current_key: Optional[str] = None) -> None:
    if _is_forbidden_float(data):
        raise DoctrinalError("DOCTRINAL_GUARD_079: numeric forbidden")

    if isinstance(data, str) and ("0.79" in data or "0.790" in data):
        if world != "PRESESION":
            raise DoctrinalError("DOCTRINAL_GUARD_079: string outside PRESESION")
        if current_key and current_key.lower() in SENSITIVE_KEYS:
            raise DoctrinalError(f"DOCTRINAL_GUARD_079: string in sensitive key {current_key}")

    if isinstance(data, dict):
        for k, v in data.items():
            _recursive_guard_079(v, world, current_key=str(k))
    elif isinstance(data, list):
        for item in data:
            _recursive_guard_079(item, world, current_key=current_key)

# -----------------------------------------
# 5. CIERRE DE ESCENARIO (MACRO)
# -----------------------------------------
def detect_scenario_close(candles: List[Any]) -> bool:
    """
    Exageración + no continuidad + desplazamiento opuesto
    """
    if len(candles) < 30:
        return False

    # 1. Hubo exageración (rango > 2.2x promedio)
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
    after = last_30[idx+1:]
    if len(after) < 4:
        return False

    # 2. No hay continuidad (nuevos extremos)
    if direction == "UP":
        if any(c.h > ex.h for c in after):
            return False
        # 3. Desplazamiento opuesto
        if after[-1].c < ex.l:
            BOT_STATE["scenario"]["closed"] = True
            BOT_STATE["scenario"]["reason"] = "PAID_PLUS_DEVELOPMENT"
            BOT_STATE["scenario"]["closed_ts"] = int(time.time())
            return True
    else:
        if any(c.l < ex.l for c in after):
            return False
        if after[-1].c > ex.h:
            BOT_STATE["scenario"]["closed"] = True
            BOT_STATE["scenario"]["reason"] = "PAID_PLUS_DEVELOPMENT"
            BOT_STATE["scenario"]["closed_ts"] = int(time.time())
            return True

    return False

# -----------------------------------------
# 4. GAP FSM (XAUUSD) — RITUAL COMPLETO
# -----------------------------------------
GapState = Literal["IDLE", "EXAGERACION", "FALLO_CONTINUIDAD", "RUPTURA", "RECUPERACION", "ACEPTACION", "TRADE_READY", "CLOSED"]

def gap_flow(candles: List[Any]) -> Dict[str, Any]:
    gs = BOT_STATE.get("gap", {}) or {}
    state: GapState = gs.get("state", "IDLE")
    tp_gap = gs.get("tp_gap", None)
    ex_dir = gs.get("direction", None)

    if len(candles) < 25:
        return {"action": "NO_TRADE", "reason": "NO_CANDLES", "gap_state": state}

    last = candles[-1]
    prev = candles[-2]
    body = abs(last.c - last.o)
    avg_body = sum(abs(c.c - c.o) for c in candles[-20:-1]) / 19.0

    next_state: GapState = state
    reason = f"GAP_WAIT_{state}"

    if state == "IDLE":
        if body > avg_body * 3.0:
            next_state = "EXAGERACION"
            tp_gap = prev.o
            ex_dir = "UP" if last.c > last.o else "DOWN"
            reason = "EXAGERACION_DETECTED"

    elif state == "EXAGERACION":
        # Continuidad viva -> descartar
        if ex_dir == "UP" and last.h > prev.h:
            next_state = "CLOSED"; reason = "GAP_DISCARDED_CONTINUITY_OK"
        elif ex_dir == "DOWN" and last.l < prev.l:
            next_state = "CLOSED"; reason = "GAP_DISCARDED_CONTINUITY_OK"
        else:
            # Fallo: primera vela a contramano con cuerpo
            if ex_dir == "UP" and last.c < last.o:
                next_state = "FALLO_CONTINUIDAD"; reason = "FALLO_CONTINUIDAD_CONFIRMED"
            elif ex_dir == "DOWN" and last.c > last.o:
                next_state = "FALLO_CONTINUIDAD"; reason = "FALLO_CONTINUIDAD_CONFIRMED"

    elif state == "FALLO_CONTINUIDAD":
        # Ruptura: desplazamiento claro
        if ex_dir == "UP" and last.c < prev.l:
            next_state = "RUPTURA"; reason = "RUPTURA_CONFIRMED"
        elif ex_dir == "DOWN" and last.c > prev.h:
            next_state = "RUPTURA"; reason = "RUPTURA_CONFIRMED"

    elif state == "RUPTURA":
        # Recuperación: vela a contramano de la ruptura (respiro)
        if ex_dir == "UP" and last.c > last.o:
            next_state = "RECUPERACION"; reason = "RECUPERACION_CONFIRMED"
        elif ex_dir == "DOWN" and last.c < last.o:
            next_state = "RECUPERACION"; reason = "RECUPERACION_CONFIRMED"

    elif state == "RECUPERACION":
        # Aceptación: continuación de la corrección
        if ex_dir == "UP" and last.c < prev.l:
            next_state = "ACEPTACION"; reason = "ACEPTACION_CONFIRMED"
        elif ex_dir == "DOWN" and last.c > prev.h:
            next_state = "ACEPTACION"; reason = "ACEPTACION_CONFIRMED"

    elif state == "ACEPTACION":
        next_state = "TRADE_READY"; reason = "RITUAL_COMPLETED"

    elif state == "TRADE_READY":
        # Pago de gap: toca/cierra hacia tp_gap
        if tp_gap is not None:
            paid = (ex_dir == "UP" and last.l <= tp_gap) or (ex_dir == "DOWN" and last.h >= tp_gap)
            if paid:
                next_state = "CLOSED"
                reason = "GAP_PAID_SCENARIO_CLOSED"
                BOT_STATE["scenario"] = {"closed": True, "reason": "PAID_PLUS_DEVELOPMENT", "closed_ts": int(time.time())}

    BOT_STATE["gap"] = {"state": next_state, "tp_gap": tp_gap, "direction": ex_dir}

    if next_state == "TRADE_READY" and tp_gap is not None:
        # GAP es TP, no gatillo. Se opera la corrección hacia el gap.
        trade_dir = "DOWN" if tp_gap < last.c else "UP"
        set_phase("ALERTADO", "TRADE")
        return {
            "action": "TRADE",
            "side": "BUY" if trade_dir == "UP" else "SELL",
            "entry": last.c,
            "sl": last.l if trade_dir == "UP" else last.h, # SL técnico simple
            "tp": tp_gap,
            "reason": reason,
            "gap_state": next_state
        }
    
    if next_state == "CLOSED":
        set_phase("IDLE", "NO_TRADE", reason)
        return {"action": "NO_TRADE", "reason": reason, "gap_state": next_state}

    set_phase("OBSERVANDO", "WAIT")
    return {"action": "WAIT", "reason": reason, "gap_state": next_state}

# -----------------------------------------
# 3. LÓGICA POI (FOREX)
# -----------------------------------------
def poi_flow(world: str, candles: List[Any], poi: Dict[str, Any]) -> Dict[str, Any]:
    checklist = {
        "contexto": True,
        "zona": False,
        "timing": False,
        "invalidacion": True,
    }

    z_low, z_high = float(poi["low"]), float(poi["high"])
    direction = poi["direction"] # UP | DOWN

    # 1. ZONA (Tocó zona reciente)
    last3 = candles[-3:]
    touched = any((c.l <= z_high and c.h >= z_low) for c in last3)
    if not touched:
        set_phase("OBSERVANDO", "WAIT")
        return {"action": "WAIT", "reason": "WAIT_ZONA", "checklist": checklist}
    checklist["zona"] = True

    # 2. INVALIDACIÓN (2 cierres en contra)
    # UP: 2 cierres < z_low
    # DOWN: 2 cierres > z_high
    closes = [c.c for c in candles[-3:]] # ultimos 3 suficiente
    invalidated = False
    if len(closes) >= 2:
        last2 = closes[-2:]
        if direction == "UP":
            invalidated = all(c < z_low for c in last2)
        else:
            invalidated = all(c > z_high for c in last2)
    
    if invalidated:
        checklist["invalidacion"] = False
        set_phase("IDLE", "NO_TRADE", "INVALIDATED_2_CLOSES")
        return {"action": "NO_TRADE", "reason": "INVALIDATED_2_CLOSES", "checklist": checklist}

    # 3. TIMING (Vela de confirmación)
    last = candles[-1]
    confirmed = (last.c > last.o) if direction == "UP" else (last.c < last.o)
    if not confirmed:
        set_phase("OBSERVANDO", "WAIT")
        return {"action": "WAIT", "reason": "WAIT_TIMING", "checklist": checklist}
    checklist["timing"] = True

    # 4. TRADE
    set_phase("ALERTADO", "TRADE")
    entry = last.c
    sl = z_low if direction == "UP" else z_high
    tp = entry + (entry - sl) * 2.5 if direction == "UP" else entry - (sl - entry) * 2.5
    
    return {
        "action": "TRADE",
        "side": "BUY" if direction == "UP" else "SELL",
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "reason": "TRADE_OK",
        "checklist": checklist
    }

# -----------------------------------------
# 2. FLUJO GENERAL DE DECISIÓN (TRONCO)
# -----------------------------------------
def decision_flow(world: str, candles: List[Any], poi: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Flujo único de decisión ATLAS
    """
    # 1. Escenario cerrado -> silencio
    if BOT_STATE["scenario"]["closed"]:
        set_phase("IDLE", "NO_TRADE", "SCENARIO_CLOSED")
        return {"action": "NO_TRADE", "reason": "SCENARIO_CLOSED"}

    # Check cierre dinámico
    if detect_scenario_close(candles):
        set_phase("IDLE", "NO_TRADE", "SCENARIO_CLOSED")
        return {"action": "NO_TRADE", "reason": "SCENARIO_CLOSED"}

    if len(candles) < 20:
        set_phase("IDLE", "NO_TRADE", "NO_CANDLES")
        return {"action": "NO_TRADE", "reason": "NO_CANDLES"}

    # 2. GAP tiene prioridad absoluta
    if world == "GAP":
        return gap_flow(candles)

    # 3. GENERAL / PRESESION
    if poi is None:
        set_phase("IDLE", "NO_TRADE", "NO_POI")
        return {"action": "NO_TRADE", "reason": "NO_POI"}

    decision = poi_flow(world, candles, poi)
    
    # Guard doctrinal final
    try:
        assert_no_079(decision, world)
    except DoctrinalError as e:
        set_phase("IDLE", "NO_TRADE", "DOCTRINAL_GUARD")
        return {"action": "NO_TRADE", "reason": str(e)}

    return decision

def evaluate_logic(world: str, symbol: str, tf: str, candles: List[Any], poi: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    # Wrapper para compatibilidad con snapshot.py
    decision = decision_flow(world, candles, poi)
    snapshot = {
        "decision": decision,
        "bot_state": {
            "phase": BOT_STATE["phase"],
            "last_decision": BOT_STATE["last_decision"],
            "reason_no_trade": BOT_STATE.get("reason_no_trade", ""),
            "last_update_ts": BOT_STATE["last_update_ts"],
        },
        "scenario": BOT_STATE["scenario"],
        "gap_info": BOT_STATE["gap"],
        "ts": int(time.time()),
    }
    return snapshot