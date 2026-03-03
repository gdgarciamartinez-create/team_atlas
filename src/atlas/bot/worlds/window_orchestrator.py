# src/atlas/bot/worlds/window_orchestrator.py
from __future__ import annotations
from typing import Dict, Any
from atlas.bot.worlds.time_windows import is_trade_window_for_world, now_local


def _detect_sweep_reversal(candles: list) -> Dict[str, Any]:
    """
    Detecta:
    - Barrida de mínimo
    - Recuperación inmediata
    """
    if len(candles) < 30:
        return {"valid": False}

    last = candles[-1]
    prev = candles[-2]

    last_low = float(last["low"])
    prev_low = float(prev["low"])
    last_close = float(last["close"])

    # Barrida + recuperación
    if last_low < prev_low and last_close > prev_low:
        return {
            "valid": True,
            "side": "BUY",
            "entry": last_close,
            "sl": last_low,
            "tp": last_close + (last_close - last_low) * 2
        }

    return {"valid": False}


def build_window_world(
    world: str,
    symbol: str,
    tf: str,
    candles: list,
    base: Dict[str, Any],
) -> Dict[str, Any]:

    w = world.upper()
    out = dict(base)

    if not is_trade_window_for_world(w):
        out["analysis"]["state"] = "WAIT"
        out["analysis"]["message"] = f"Fuera de ventana ({w})"
        return out

    # ----------------------
    # GAP WORLD REAL
    # ----------------------
    if w == "GAP":
        setup = _detect_sweep_reversal(candles)

        if setup["valid"]:
            out["analysis"]["state"] = "GATILLO"
            out["analysis"]["message"] = "Barrida + recuperación confirmada"

            out["plan_frozen"] = {
                "side": setup["side"],
                "entry": round(setup["entry"], 2),
                "sl": round(setup["sl"], 2),
                "tp": round(setup["tp"], 2),
            }

            out["alert"] = {
                "type": "signal",
                "side": setup["side"],
                "symbol": symbol
            }

            return out

        out["analysis"]["state"] = "ZONA"
        out["analysis"]["message"] = "En ventana GAP - esperando barrida"
        return out

    # ----------------------
    # Otros mundos (placeholder)
    # ----------------------
    out["analysis"]["state"] = "ZONA"
    out["analysis"]["message"] = f"En ventana ({w}) - lógica aún no aplicada"
    return out