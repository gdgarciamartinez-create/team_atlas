from __future__ import annotations
from typing import Dict, List, Tuple, Any


# =========================================================
# Utilidades internas
# =========================================================

def _last_impulse(candles: List[Dict[str, Any]]):
    if len(candles) < 20:
        return None

    high = max(c["h"] for c in candles[-20:])
    low = min(c["l"] for c in candles[-20:])

    if high == low:
        return None

    direction = "BUY" if candles[-1]["c"] > candles[-10]["c"] else "SELL"

    return {
        "high": high,
        "low": low,
        "dir": direction,
        "range": abs(high - low)
    }


def _fib_zone(impulse):
    high = impulse["high"]
    low = impulse["low"]
    direction = impulse["dir"]

    if direction == "BUY":
        fib_618 = high - (high - low) * 0.618
        fib_786 = high - (high - low) * 0.786
        return min(fib_618, fib_786), max(fib_618, fib_786)

    else:
        fib_618 = low + (high - low) * 0.618
        fib_786 = low + (high - low) * 0.786
        return min(fib_618, fib_786), max(fib_618, fib_786)


# =========================================================
# Motor principal
# =========================================================

def run_world_rows(
    world: str,
    tf: str,
    symbols: List[str],
    candles_by_symbol: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:

    symbol = symbols[0]
    payload = candles_by_symbol[symbol]
    candles = payload["candles"]

    impulse = _last_impulse(candles)
    if not impulse:
        return (
            {"world": world, "action": "WAIT", "signals": 0, "reason": "Sin impulso"},
            [{
                "symbol": symbol,
                "tf": tf,
                "text": "WAIT (sin impulso)",
                "action": "WAIT",
                "side": None,
                "entry": None,
                "sl": None,
                "tp": None,
            }]
        )

    z_low, z_high = _fib_zone(impulse)
    last_price = candles[-1]["c"]

    if not (z_low <= last_price <= z_high):
        return (
            {"world": world, "action": "WAIT", "signals": 0, "reason": "Fuera zona fib"},
            [{
                "symbol": symbol,
                "tf": tf,
                "text": "WAIT (fuera zona fib)",
                "action": "WAIT",
                "side": None,
                "entry": None,
                "sl": None,
                "tp": None,
            }]
        )

    direction = impulse["dir"]

    sl = impulse["low"] if direction == "BUY" else impulse["high"]
    tp = impulse["high"] if direction == "BUY" else impulse["low"]

    return (
        {"world": world, "action": direction, "signals": 1, "reason": "Zona fib válida"},
        [{
            "symbol": symbol,
            "tf": tf,
            "text": f"{direction} (zona fib)",
            "action": direction,
            "side": direction,
            "entry": last_price,
            "sl": sl,
            "tp": tp,
        }]
    )
