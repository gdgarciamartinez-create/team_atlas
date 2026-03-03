# src/atlas/bot/impulse.py
from atlas.bot.state import BOT_STATE

MIN_CANDLES = 20
IMPULSE_MIN_RANGE = 1.2

def detect_impulse():
    candles = BOT_STATE.get("candles", [])
    if not isinstance(candles, list) or len(candles) < MIN_CANDLES:
        return {"has_impulse": False, "reason": "NO_HAY_VELAS"}

    last = candles[-10:]
    highs = [c.get("high") for c in last]
    lows = [c.get("low") for c in last]
    if not highs or not lows:
        return {"has_impulse": False, "reason": "DATOS_INVALIDOS"}

    total_range = max(highs) - min(lows)
    avg_range = sum((c["high"] - c["low"]) for c in last) / len(last)

    if avg_range <= 0:
        return {"has_impulse": False, "reason": "RANGO_INVALIDO"}

    if total_range >= avg_range * IMPULSE_MIN_RANGE:
        direction = "UP" if last[-1]["close"] > last[0]["open"] else "DOWN"
        return {"has_impulse": True, "direction": direction, "range": round(total_range, 5)}

    return {"has_impulse": False, "reason": "SIN_EXPANSION"}