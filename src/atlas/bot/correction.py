# src/atlas/bot/correction.py
from atlas.bot.state import BOT_STATE

CORRECTION_MIN = 0.25
CORRECTION_MAX = 0.8

def detect_correction(impulse):
    candles = BOT_STATE.get("candles", [])
    if not impulse.get("has_impulse"):
        return {"has_correction": False, "reason": "SIN_IMPULSO"}

    if not isinstance(candles, list) or len(candles) < 5:
        return {"has_correction": False, "reason": "NO_HAY_VELAS"}

    recent = candles[-5:]
    highs = [c["high"] for c in recent]
    lows = [c["low"] for c in recent]
    corr_range = max(highs) - min(lows)

    imp_range = float(impulse.get("range", 0) or 0)
    if imp_range <= 0:
        return {"has_correction": False, "reason": "RANGO_IMPULSO_INVALIDO"}

    ratio = corr_range / imp_range
    if CORRECTION_MIN <= ratio <= CORRECTION_MAX:
        return {"has_correction": True, "ratio": round(ratio, 3)}

    return {"has_correction": False, "ratio": round(ratio, 3), "reason": "FUERA_DE_RANGO"}