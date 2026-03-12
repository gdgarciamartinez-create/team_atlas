from __future__ import annotations

from typing import Any, Dict, List, Optional


def _num(v: Any) -> Optional[float]:
    try:
        return float(v)
    except Exception:
        return None


def _h(c: Dict[str, Any]) -> Optional[float]:
    return _num(c.get("h", c.get("high")))


def _l(c: Dict[str, Any]) -> Optional[float]:
    return _num(c.get("l", c.get("low")))


def _o(c: Dict[str, Any]) -> Optional[float]:
    return _num(c.get("o", c.get("open")))


def _c(c: Dict[str, Any]) -> Optional[float]:
    return _num(c.get("c", c.get("close")))


def detect_sweep(
    candles: List[Dict[str, Any]],
    side: str,
    lookback: int = 12,
) -> Dict[str, Any]:

    side = str(side or "").upper().strip()

    if len(candles) < max(lookback + 2, 8):
        return {
            "valid": False,
            "reason": "not_enough_candles",
            "level": None,
            "strength": 0.0,
        }

    last = candles[-1]
    prev = candles[-(lookback + 1):-1]

    last_open = _o(last)
    last_close = _c(last)
    last_high = _h(last)
    last_low = _l(last)

    if None in (last_open, last_close, last_high, last_low):
        return {
            "valid": False,
            "reason": "bad_last_candle",
            "level": None,
            "strength": 0.0,
        }

    highs = [_h(x) for x in prev]
    lows = [_l(x) for x in prev]

    highs = [x for x in highs if x is not None]
    lows = [x for x in lows if x is not None]

    if not highs or not lows:
        return {
            "valid": False,
            "reason": "bad_history",
            "level": None,
            "strength": 0.0,
        }

    prev_high = max(highs)
    prev_low = min(lows)

    body = abs(last_close - last_open)
    full_range = abs(last_high - last_low)

    if full_range <= 0:
        return {
            "valid": False,
            "reason": "flat_candle",
            "level": None,
            "strength": 0.0,
        }

    rejection_ratio = (full_range - body) / full_range

    # tolerancia recuperación parcial
    mid_recovery = last_low + full_range * 0.45
    mid_recovery_sell = last_high - full_range * 0.45

    if side == "BUY":

        swept = last_low < prev_low
        recovered = last_close > prev_low or last_close > mid_recovery
        bullish_close = last_close >= last_open

        valid = swept and recovered and bullish_close

        strength = 0.0

        if swept:
            overshoot = prev_low - last_low

            strength = (
                (overshoot / full_range) * 0.6
                + rejection_ratio * 0.4
            )

        return {
            "valid": valid,
            "reason": "buy_sweep" if valid else "buy_no_sweep",
            "level": prev_low,
            "strength": round(strength, 4),
            "overshoot": round(prev_low - last_low, 6) if swept else 0.0,
            "rejection_ratio": round(rejection_ratio, 4),
        }

    if side == "SELL":

        swept = last_high > prev_high
        recovered = last_close < prev_high or last_close < mid_recovery_sell
        bearish_close = last_close <= last_open

        valid = swept and recovered and bearish_close

        strength = 0.0

        if swept:
            overshoot = last_high - prev_high

            strength = (
                (overshoot / full_range) * 0.6
                + rejection_ratio * 0.4
            )

        return {
            "valid": valid,
            "reason": "sell_sweep" if valid else "sell_no_sweep",
            "level": prev_high,
            "strength": round(strength, 4),
            "overshoot": round(last_high - prev_high, 6) if swept else 0.0,
            "rejection_ratio": round(rejection_ratio, 4),
        }

    return {
        "valid": False,
        "reason": "invalid_side",
        "level": None,
        "strength": 0.0,
    }