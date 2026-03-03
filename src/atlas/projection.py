from atlas.bot.state import BOT_STATE

def build_projection(structure: dict) -> dict:
    """
    Proyección simple y consistente:
    - Base: usar el rango del impulso detectado (structure.impulse.range)
    - Dirección: UP/DOWN
    - TP1: 0.618 del rango desde el punto actual
    - TP: 1.0 del rango desde el punto actual
    - Si hay fibonacci válido, se usa como “zona de re-enganche” y se proyecta hacia el siguiente POI por extensión.
    """
    candles = BOT_STATE.get("candles", [])
    if not isinstance(candles, list) or len(candles) < 5:
        return {"valid": False, "reason": "NOT_ENOUGH_CANDLES"}

    impulse = structure.get("impulse", {})
    if not impulse.get("has_impulse"):
        return {"valid": False, "reason": "NO_IMPULSE"}

    direction = impulse.get("direction", "UP")
    rng = float(impulse.get("range", 0) or 0)
    if rng <= 0:
        return {"valid": False, "reason": "INVALID_RANGE"}

    price = float(candles[-1]["close"])
    # Proyección tipo “onda 5 simple”: continuidad tras corrección
    if direction == "UP":
        tp1 = price + (rng * 0.618)
        tp = price + (rng * 1.0)
    else:
        tp1 = price - (rng * 0.618)
        tp = price - (rng * 1.0)

    # Si hay fib calculado, anexar info útil para UI/MT5
    fib = (structure.get("fibonacci") or {})
    return {
        "valid": True,
        "direction": direction,
        "price": round(price, 5),
        "tp1": round(tp1, 5),
        "tp": round(tp, 5),
        "basis": "IMPULSE_RANGE_EXT",
        "fibonacci": {
            "fib_786": fib.get("fib_786"),
            "fib_79": fib.get("fib_79"),
            "in_zone": fib.get("in_zone"),
        } if isinstance(fib, dict) else None,
    }