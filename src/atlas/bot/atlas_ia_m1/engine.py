from __future__ import annotations
from typing import Dict, List, Tuple, Any


def _micro_impulse(candles: List[Dict[str, Any]]):
    if len(candles) < 10:
        return None

    high = max(c["h"] for c in candles[-10:])
    low = min(c["l"] for c in candles[-10:])

    if high == low:
        return None

    direction = "BUY" if candles[-1]["c"] > candles[-5]["c"] else "SELL"

    return {
        "high": high,
        "low": low,
        "dir": direction,
        "range": abs(high - low)
    }


def run_world_rows(
    world: str,
    tf: str,
    symbols: List[str],
    candles_by_symbol: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:

    symbol = symbols[0]
    payload = candles_by_symbol[symbol]
    candles = payload["candles"]

    impulse = _micro_impulse(candles)
    if not impulse:
        return (
            {"world": world, "action": "WAIT", "signals": 0, "reason": "Sin micro impulso"},
            [{
                "symbol": symbol,
                "tf": tf,
                "text": "WAIT (micro vacío)",
                "action": "WAIT",
                "side": None,
                "entry": None,
                "sl": None,
                "tp": None,
            }]
        )

    last_price = candles[-1]["c"]
    direction = impulse["dir"]

    sl = impulse["low"] if direction == "BUY" else impulse["high"]
    tp = last_price + (impulse["range"] * 0.5) if direction == "BUY" else last_price - (impulse["range"] * 0.5)

    return (
        {"world": world, "action": direction, "signals": 1, "reason": "Micro reacción"},
        [{
            "symbol": symbol,
            "tf": tf,
            "text": f"{direction} (micro)",
            "action": direction,
            "side": direction,
            "entry": last_price,
            "sl": sl,
            "tp": tp,
        }]
    )
