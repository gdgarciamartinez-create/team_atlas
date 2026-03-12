from __future__ import annotations

from typing import Dict, List, Tuple, Any

from atlas.api.risk import calc_lots_from_score
from atlas.bot.analysis.sweep import detect_sweep
from atlas.bot.analysis.scoring import calc_score


def _last_impulse(candles: List[Dict[str, Any]]):
    if len(candles) < 36:
        return None

    window = candles[-36:]
    high = max(c["h"] for c in window)
    low = min(c["l"] for c in window)

    if high == low:
        return None

    direction = "BUY" if candles[-1]["c"] > candles[-18]["c"] else "SELL"

    return {
        "high": high,
        "low": low,
        "dir": direction,
        "range": abs(high - low),
    }


def _fib_zone(impulse):
    high = float(impulse["high"])
    low = float(impulse["low"])
    direction = impulse["dir"]

    if direction == "BUY":
        fib_618 = high - (high - low) * 0.618
        fib_786 = high - (high - low) * 0.786
        return min(fib_618, fib_786), max(fib_618, fib_786)

    fib_618 = low + (high - low) * 0.618
    fib_786 = low + (high - low) * 0.786
    return min(fib_618, fib_786), max(fib_618, fib_786)


def _rr(entry: float, sl: float, tp: float) -> float:
    risk = abs(entry - sl)
    reward = abs(tp - entry)
    if risk <= 0:
        return 0.0
    return reward / risk


def _build_wait_row(symbol: str, tf: str, note: str) -> Dict[str, Any]:
    return {
        "symbol": symbol,
        "tf": tf,
        "score": 0,
        "state": "SIN_SETUP",
        "text": note,
        "action": "WAIT",
        "side": None,
        "entry": None,
        "sl": None,
        "tp": None,
        "parcial": None,
        "lot": None,
        "risk_percent": 0.0,
        "rr": 0.0,
        "sweep_valid": False,
        "sweep_strength": 0.0,
        "note": note,
        "zone_low": None,
        "zone_high": None,
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

    if not isinstance(candles, list) or len(candles) < 36:
        row = _build_wait_row(symbol, tf, "Sin impulso")
        return (
            {
                "world": world,
                "action": "WAIT",
                "signals": 0,
                "reason": "Sin impulso",
                "score": 0,
            },
            [row],
        )

    impulse = _last_impulse(candles)
    if not impulse:
        row = _build_wait_row(symbol, tf, "Sin impulso")
        return (
            {
                "world": world,
                "action": "WAIT",
                "signals": 0,
                "reason": "Sin impulso",
                "score": 0,
            },
            [row],
        )

    z_low, z_high = _fib_zone(impulse)
    last_price = float(candles[-1]["c"])
    direction = impulse["dir"]
    impulse_range = float(impulse["range"])

    if impulse_range <= 0:
        row = _build_wait_row(symbol, tf, "Rango inválido")
        return (
            {
                "world": world,
                "action": "WAIT",
                "signals": 0,
                "reason": "Rango inválido",
                "score": 0,
            },
            [row],
        )

    zone_buffer = impulse_range * 0.08
    inside_zone = z_low <= last_price <= z_high
    near_zone = (z_low - zone_buffer) <= last_price <= (z_high + zone_buffer)

    sweep = detect_sweep(candles, side=direction, lookback=14)

    sl = float(impulse["low"]) if direction == "BUY" else float(impulse["high"])
    tp = (
        last_price + (impulse_range * 2.2)
        if direction == "BUY"
        else last_price - (impulse_range * 2.2)
    )
    parcial = last_price + (tp - last_price) * 0.40

    rr = _rr(last_price, sl, tp)

    timing_ok = inside_zone or near_zone
    context_ok = True
    late_entry = not near_zone
    structure_dirty = False
    spread_bad = False
    confluence_bonus = 2 if inside_zone else (1 if near_zone else 0)

    score_pack = calc_score(
        side=direction,
        entry=last_price,
        sl=sl,
        tp=tp,
        sweep=sweep,
        context_ok=context_ok,
        timing_ok=timing_ok,
        zone_touch_count=1,
        late_entry=late_entry,
        structure_dirty=structure_dirty,
        spread_bad=spread_bad,
        confluence_bonus=confluence_bonus,
    )

    score = int(score_pack["score"])
    state = score_pack["state"]

    if not near_zone and not sweep["valid"]:
        score = min(score, 8)
        state = "SIN_SETUP"

    lots, risk_percent = calc_lots_from_score(
        symbol=symbol,
        entry=last_price,
        sl=sl,
        score=score,
    )

    row = {
        "symbol": symbol,
        "tf": tf,
        "score": score,
        "state": state,
        "text": f"{direction} scalping extendido" if state != "SIN_SETUP" else "SIN_SETUP",
        "action": direction if state in {"SET_UP", "ENTRY"} else "WAIT",
        "side": direction if state in {"SET_UP", "ENTRY"} else None,
        "entry": last_price if state in {"SET_UP", "ENTRY"} else None,
        "sl": sl if state in {"SET_UP", "ENTRY"} else None,
        "tp": tp if state in {"SET_UP", "ENTRY"} else None,
        "parcial": parcial if state in {"SET_UP", "ENTRY"} else None,
        "lot": lots if state in {"SET_UP", "ENTRY"} and lots > 0 else None,
        "risk_percent": risk_percent,
        "rr": rr,
        "zone_low": z_low,
        "zone_high": z_high,
        "sweep_valid": sweep["valid"],
        "sweep_strength": sweep["strength"],
        "candles": candles,
        "note": f'{state} · score {score} · RR {score_pack["rr"]} · {sweep["reason"]}',
    }

    analysis = {
        "world": world,
        "action": direction if state in {"SET_UP", "ENTRY"} else "WAIT",
        "signals": 1 if state in {"SET_UP", "ENTRY"} else 0,
        "reason": row["note"],
        "score": score,
        "side": direction,
        "state": state,
        "rr": score_pack["rr"],
        "sweep_valid": sweep["valid"],
        "zone_low": z_low,
        "zone_high": z_high,
    }

    return analysis, [row]