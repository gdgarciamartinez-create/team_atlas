from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import time

from atlas.bot.state import BOT_STATE, set_phase
from atlas.core.doctrine_guard import assert_no_079

# GAP FSM: si existe, lo usamos. Si no existe, no rompemos.
try:
    from atlas.core.gap_fsm import gap_step, TRADE_READY
except Exception:
    gap_step = None
    TRADE_READY = "TRADE_READY"


def _is_candle_obj(c: Any) -> bool:
    return all(hasattr(c, k) for k in ("o", "h", "l", "c"))

def _scenario_close(candles: List[Any]) -> bool:
    """
    Cierre macro (pago + desarrollo). Heurística simple:
    - Exageración (rango > 2.2x promedio en últimas 30)
    - Luego NO hace nuevos extremos en esa dirección
    - Termina con desplazamiento opuesto
    """
    if len(candles) < 30:
        return False
    if not _is_candle_obj(candles[-1]):
        return False

    last_30 = candles[-30:]
    ranges = [(c.h - c.l) for c in last_30]
    avg = (sum(ranges[:15]) / 15.0) if sum(ranges[:15]) > 0 else 1.0

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
        if any(x.h > ex.h for x in after):
            return False
        return after[-1].c < ex.l
    else:
        if any(x.l < ex.l for x in after):
            return False
        return after[-1].c > ex.h


def _new_checklist() -> Dict[str, bool]:
    return {
        "contexto": False,
        "fibo_786": False,
        "zona": False,
        "timing": False,
        "invalidacion_2_cierres": True,
        "escenario_abierto": True,
    }


def _invalidated_by_two_closes(closes: List[float], z_low: float, z_high: float, direction: str) -> bool:
    if len(closes) < 2:
        return False
    last2 = closes[-2:]
    if direction == "UP":
        return all(c < z_low for c in last2)
    return all(c > z_high for c in last2)


def _timing_confirmed(last: Any, direction: str) -> bool:
    if direction == "UP":
        return last.c > last.o
    return last.c < last.o


def decide_general(world: str, symbol: str, tf: str, candles: List[Any], poi: Dict[str, Any]) -> Dict[str, Any]:
    checklist = _new_checklist()

    # Escenario cerrado (persistente)
    if BOT_STATE.get("scenario", {}).get("closed", False):
        checklist["escenario_abierto"] = False
        set_phase("IDLE", "NO_TRADE", "SCENARIO_CLOSED")
        return {"action": "NO_TRADE", "reason": "SCENARIO_CLOSED", "confidence": 0.0, "checklist": checklist}

    # Cierre macro por pago+desarrollo
    if _scenario_close(candles):
        BOT_STATE["scenario"] = {"closed": True, "reason": "PAID_PLUS_DEVELOPMENT", "closed_ts": int(time.time())}
        checklist["escenario_abierto"] = False
        set_phase("IDLE", "NO_TRADE", "SCENARIO_CLOSED")
        return {"action": "NO_TRADE", "reason": "SCENARIO_CLOSED", "confidence": 0.0, "checklist": checklist}

    if len(candles) < 20:
        set_phase("IDLE", "NO_TRADE", "NO_CANDLES")
        return {"action": "NO_TRADE", "reason": "NO_CANDLES", "confidence": 0.0, "checklist": checklist}

    checklist["contexto"] = True
    checklist["fibo_786"] = True  # validación obligatoria (sin usar 0.79)

    z_low = float(poi["low"])
    z_high = float(poi["high"])
    direction = (poi.get("direction") or "UP").strip().upper()  # UP / DOWN

    # Zona tocada (últimas 3 velas)
    last3 = candles[-3:]
    touched = any((c.l <= z_high and c.h >= z_low) for c in last3)
    if not touched:
        set_phase("OBSERVANDO", "WAIT")
        return {"action": "WAIT", "reason": "WAIT_ZONA", "confidence": 0.35, "checklist": checklist}
    checklist["zona"] = True

    # Invalidación por 2 cierres en contra
    closes = [float(c.c) for c in candles]
    if _invalidated_by_two_closes(closes, z_low, z_high, direction):
        checklist["invalidacion_2_cierres"] = False
        set_phase("IDLE", "NO_TRADE", "INVALIDATED_BY_TWO_CLOSES")
        return {"action": "NO_TRADE", "reason": "INVALIDATED_BY_TWO_CLOSES", "confidence": 0.0, "checklist": checklist}

    # Timing mínimo
    if not _timing_confirmed(candles[-1], direction):
        set_phase("OBSERVANDO", "WAIT")
        return {"action": "WAIT", "reason": "WAIT_TIMING", "confidence": 0.6, "checklist": checklist}
    checklist["timing"] = True

    # Señal LAB
    entry = float(candles[-1].c)
    if direction == "UP":
        side = "BUY"
        sl = z_low
        tp = entry + (entry - sl) * 2.5
    else:
        side = "SELL"
        sl = z_high
        tp = entry - (sl - entry) * 2.5

    if (side == "BUY" and entry <= sl) or (side == "SELL" and entry >= sl):
        set_phase("IDLE", "NO_TRADE", "BAD_RISK_GEOMETRY")
        return {"action": "NO_TRADE", "reason": "BAD_RISK_GEOMETRY", "confidence": 0.0, "checklist": checklist}

    set_phase("ALERTADO", "TRADE")
    return {
        "action": "TRADE",
        "side": side,
        "entry": entry,
        "sl": float(sl),
        "tp": float(tp),
        "reason": "TRADE_OK",
        "confidence": 1.0,
        "checklist": checklist,
        "tags": ["lab_signal"],
    }


def evaluate(world: str, symbol: str, tf: str, candles: List[Any], poi: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    world_u = (world or "GENERAL").strip().upper()

    # Guardia doctrinal (snapshot final, no tocar en claves sensibles)
    gap_info = None

    # Prioridad GAP
    if world_u == "GAP" and symbol == "XAUUSD" and gap_step is not None:
        st, steps, reason, tp_gap = gap_step(candles)
        gap_info = {"state": st, "steps": steps, "reason": reason, "tp_gap": tp_gap}

        if st == TRADE_READY and tp_gap is not None and len(candles) >= 10:
            # zona técnica mínima con últimas 5 velas
            last5 = candles[-5:]
            z_low = min(c.l for c in last5)
            z_high = max(c.h for c in last5)

            # trade_dir según dónde está el gap vs precio actual
            curr = float(candles[-1].c)
            trade_dir = "DOWN" if float(tp_gap) < curr else "UP"
            poi2 = {"low": z_low, "high": z_high, "direction": trade_dir}

            decision = decide_general(world_u, symbol, tf, candles, poi2)
            decision["tp"] = float(tp_gap)  # GAP es TP principal
            decision["reason"] = "GAP_TRADE_READY"
        else:
            set_phase("OBSERVANDO", "WAIT")
            decision = {"action": "WAIT", "reason": reason, "confidence": 0.25, "checklist": {"gap_ritual": False}}

    else:
        if poi is None:
            set_phase("IDLE", "NO_TRADE", "NO_POI")
            decision = {"action": "NO_TRADE", "reason": "NO_POI", "confidence": 0.0, "checklist": _new_checklist()}
        else:
            decision = decide_general(world_u, symbol, tf, candles, poi)

    snap = {
        "ts": int(time.time()),
        "decision": decision,
        "gap_info": gap_info,
        "bot_state": {
            "phase": BOT_STATE.get("phase", "IDLE"),
            "last_decision": BOT_STATE.get("last_decision", "NO_TRADE"),
            "reason_no_trade": BOT_STATE.get("reason_no_trade", ""),
            "scenario": BOT_STATE.get("scenario", {}),
            "gap": BOT_STATE.get("gap", {}),
            "last_update_ts": BOT_STATE.get("last_update_ts", 0),
        },
    }

    # Guard doctrinal final (no 0.79)
    try:
        assert_no_079(snap, world_u)
        snap["doctrine_ok"] = True
    except Exception as e:
        set_phase("IDLE", "NO_TRADE", "DOCTRINAL_GUARD")
        snap["doctrine_ok"] = False
        snap["decision"] = {"action": "NO_TRADE", "reason": "DOCTRINAL_GUARD", "confidence": 0.0, "checklist": {"doctrina": False}}
        snap["last_error"] = str(e)[:160]

    return snap
