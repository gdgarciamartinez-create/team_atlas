# src/atlas/bot/fibonacci.py
from atlas.bot.state import BOT_STATE

FIB_MIN = 0.786
FIB_MAX = 0.79

def compute_fibonacci(structure):
    if not structure.get("continuity_ok"):
        return {"valid": False, "reason": "NO_CONTEXT"}

    candles = BOT_STATE.get("candles", [])
    if not isinstance(candles, list) or len(candles) < 10:
        return {"valid": False, "reason": "FALTAN_VELAS"}

    impulse = structure.get("impulse", {})
    direction = impulse.get("direction")

    last = candles[-10:]
    high = max(c["high"] for c in last)
    low = min(c["low"] for c in last)
    if high <= low:
        return {"valid": False, "reason": "NO_CONTEXT"}

    price = float(candles[-1]["close"])

    if direction == "UP":
        fib_786 = high - (high - low) * FIB_MIN
        fib_79 = high - (high - low) * FIB_MAX
        in_zone = min(fib_786, fib_79) <= price <= max(fib_786, fib_79)
    else:
        fib_786 = low + (high - low) * FIB_MIN
        fib_79 = low + (high - low) * FIB_MAX
        in_zone = min(fib_786, fib_79) <= price <= max(fib_786, fib_79)

    return {
        "valid": True,
        "direction": direction,
        "high": round(high, 5),
        "low": round(low, 5),
        "fib_786": round(fib_786, 5),
        "fib_79": round(fib_79, 5),
        "price": round(price, 5),
        "in_zone": bool(in_zone),
    }