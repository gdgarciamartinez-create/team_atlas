from __future__ import annotations
from typing import Dict, Any, List
from dataclasses import dataclass

# =========================================================
# CONFIGURACIÓN FINAL
# =========================================================

SCALP_CONFIG = {
    "SCALP_M1": {
        "min_rr_tp1": 0.8,
        "confirm_closes": 2,
        "max_idle_candles": 6,
    },
    "SCALP_M5": {
        "min_rr_tp1": 1.0,
        "confirm_closes": 2,
        "max_idle_candles": 10,
    }
}

# =========================================================
# UTILIDADES FIBO
# =========================================================

def fibo_levels(high: float, low: float) -> Dict[str, float]:
    diff = high - low
    return {
        "0.618": high - diff * 0.618,
        "0.786": high - diff * 0.786,
        "1.0": low
    }

def detect_impulse(candles: List[Dict[str, Any]]) -> Dict[str, float] | None:
    if len(candles) < 20:
        return None

    recent = candles[-20:]
    high = max(c["h"] for c in recent)
    low = min(c["l"] for c in recent)

    if high == low:
        return None

    return {"high": high, "low": low}

def confirm_rejection(candles: List[Dict[str, Any]], level: float, closes: int) -> bool:
    recent = candles[-closes:]
    return all(c["c"] > level for c in recent)

# =========================================================
# MOTOR PRINCIPAL
# =========================================================

def run_scalping(
    symbol: str,
    candles: List[Dict[str, Any]],
    atlas_mode: str,
    state: Dict[str, Any]
) -> Dict[str, Any]:

    if atlas_mode not in SCALP_CONFIG:
        return {"status": "WAIT", "reason": "Modo no válido"}

    config = SCALP_CONFIG[atlas_mode]

    if len(candles) < 30:
        return {"status": "WAIT", "reason": "Datos insuficientes"}

    impulse = detect_impulse(candles)
    if not impulse:
        return {"status": "WAIT", "reason": "Sin impulso claro"}

    fib = fibo_levels(impulse["high"], impulse["low"])
    last_price = candles[-1]["c"]

    # =========================
    # WAIT → WAIT_GATILLO
    # =========================

    if state.get("status") == "WAIT":
        if abs(last_price - fib["0.786"]) < abs(impulse["high"] - impulse["low"]) * 0.01:
            state.update({
                "status": "WAIT_GATILLO",
                "zone": fib["0.786"],
                "impulse": impulse,
            })
            return {"status": "WAIT_GATILLO", "reason": "Zona válida detectada"}

        return {"status": "WAIT", "reason": "Fuera de zona"}

    # =========================
    # WAIT_GATILLO → SIGNAL
    # =========================

    if state.get("status") == "WAIT_GATILLO":

        zone = state["zone"]

        if confirm_rejection(candles, zone, config["confirm_closes"]):

            entry = candles[-1]["c"]
            sl = state["impulse"]["low"]
            risk = entry - sl
            tp = entry + risk * config["min_rr_tp1"]

            state.update({
                "status": "SIGNAL",
                "entry": entry,
                "sl": sl,
                "tp": tp
            })

            return {
                "status": "SIGNAL",
                "side": "BUY",
                "entry": entry,
                "sl": sl,
                "tp": tp
            }

        return {"status": "WAIT_GATILLO", "reason": "Esperando confirmación"}

    # =========================
    # SIGNAL MANTENIDO
    # =========================

    if state.get("status") == "SIGNAL":
        return {
            "status": "SIGNAL",
            "side": "BUY",
            "entry": state["entry"],
            "sl": state["sl"],
            "tp": state["tp"]
        }

    return {"status": "WAIT", "reason": "Estado desconocido"}
