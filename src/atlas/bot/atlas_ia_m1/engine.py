from __future__ import annotations

from typing import Any, Dict, List, Tuple

from atlas.api.risk import calc_lots_from_score
from atlas.bot.analysis.scoring import calc_score
from atlas.bot.analysis.sweep import detect_sweep


def _micro_impulse(candles: List[Dict[str, Any]]):
    if len(candles) < 20:
        return None

    window = candles[-20:]
    high = max(c["h"] for c in window)
    low = min(c["l"] for c in window)

    if high == low:
        return None

    direction = "BUY" if candles[-1]["c"] > candles[-10]["c"] else "SELL"

    return {
        "high": high,
        "low": low,
        "dir": direction,
        "range": abs(high - low),
    }


def _zone_from_impulse(impulse: Dict[str, Any]) -> Tuple[float, float]:
    high = float(impulse["high"])
    low = float(impulse["low"])
    direction = impulse["dir"]

    if direction == "BUY":
        z1 = high - (high - low) * 0.382
        z2 = high - (high - low) * 0.786
        return min(z1, z2), max(z1, z2)

    z1 = low + (high - low) * 0.382
    z2 = low + (high - low) * 0.786
    return min(z1, z2), max(z1, z2)


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
        "tp1": None,
        "tp1_price": None,
        "tp2": None,
        "parcial": None,
        "lot": None,
        "risk_percent": 0.0,
        "rr": 0.0,
        "sweep_valid": False,
        "sweep_strength": 0.0,
        "note": note,
    }


def _consecutive_closes_ok(candles: List[Dict[str, Any]], side: str) -> bool:
    if len(candles) < 3:
        return False

    c1 = float(candles[-2]["c"])
    o1 = float(candles[-2]["o"])
    c2 = float(candles[-1]["c"])
    o2 = float(candles[-1]["o"])

    if side == "BUY":
        return c1 > o1 and c2 > o2 and c2 >= c1
    return c1 < o1 and c2 < o2 and c2 <= c1


def _impulse_followthrough_ok(candles: List[Dict[str, Any]], side: str) -> bool:
    if len(candles) < 4:
        return False

    closes = [float(c["c"]) for c in candles[-4:]]

    if side == "BUY":
        advances = 0
        for i in range(1, len(closes)):
            if closes[i] >= closes[i - 1]:
                advances += 1
        return advances >= 2

    declines = 0
    for i in range(1, len(closes)):
        if closes[i] <= closes[i - 1]:
            declines += 1
    return declines >= 2


def _distance_from_sweep_ok(
    candles: List[Dict[str, Any]],
    side: str,
    last_price: float,
    sl: float,
) -> bool:
    if len(candles) < 2:
        return False

    risk = abs(last_price - sl)
    if risk <= 0:
        return False

    last_candle = candles[-1]
    low = float(last_candle["l"])
    high = float(last_candle["h"])

    min_required = risk * 0.30

    if side == "BUY":
        travelled = last_price - low
        return travelled >= min_required

    travelled = high - last_price
    return travelled >= min_required


def _outside_dead_zone(
    last_price: float,
    zone_low: float,
    zone_high: float,
) -> bool:
    zone_size = abs(zone_high - zone_low)
    if zone_size <= 0:
        return False

    dead = zone_size * 0.10
    inner_low = zone_low + dead
    inner_high = zone_high - dead

    return not (inner_low <= last_price <= inner_high)


def _resolve_state(
    score: int,
    inside_zone: bool,
    near_zone: bool,
    sweep_valid: bool,
    double_close_ok: bool,
    followthrough_ok: bool,
    distance_ok: bool,
    dead_zone_ok: bool,
) -> str:
    if (
        inside_zone
        and sweep_valid
        and score >= 9
        and (double_close_ok or followthrough_ok)
        and distance_ok
        and dead_zone_ok
    ):
        return "ENTRY"

    if inside_zone and score >= 8 and dead_zone_ok:
        return "SET_UP"

    if near_zone and score >= 7 and dead_zone_ok:
        return "SET_UP"

    if sweep_valid and score >= 7 and dead_zone_ok:
        return "SET_UP"

    return "SIN_SETUP"


def _setup_type(
    sweep_valid: bool,
    double_close_ok: bool,
    followthrough_ok: bool,
    inside_zone: bool,
    near_zone: bool,
) -> str:
    if sweep_valid and (double_close_ok or followthrough_ok):
        return "m1_sweep_reclaim"
    if followthrough_ok:
        return "m1_followthrough_entry"
    if inside_zone or near_zone:
        return "m1_zone_reaction"
    return "m1_break_retest"


def run_world_rows(
    world: str,
    tf: str,
    symbols: List[str],
    candles_by_symbol: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    symbol = symbols[0]
    payload = candles_by_symbol[symbol]
    candles = payload["candles"]

    if not isinstance(candles, list) or len(candles) < 20:
        row = _build_wait_row(symbol, tf, "Sin micro impulso")
        return (
            {
                "world": world,
                "action": "WAIT",
                "signals": 0,
                "reason": "Sin micro impulso",
                "score": 0,
            },
            [row],
        )

    impulse = _micro_impulse(candles)
    if not impulse:
        row = _build_wait_row(symbol, tf, "Sin micro impulso")
        return (
            {
                "world": world,
                "action": "WAIT",
                "signals": 0,
                "reason": "Sin micro impulso",
                "score": 0,
            },
            [row],
        )

    last = candles[-1]
    last_price = float(last["c"])
    direction = impulse["dir"]
    impulse_range = float(impulse["range"])
    zone_low, zone_high = _zone_from_impulse(impulse)

    if impulse_range <= 0:
        row = _build_wait_row(symbol, tf, "Rango invalido")
        return (
            {
                "world": world,
                "action": "WAIT",
                "signals": 0,
                "reason": "Rango invalido",
                "score": 0,
            },
            [row],
        )

    zone_buffer = impulse_range * 0.15
    inside_zone = zone_low <= last_price <= zone_high
    near_zone = (zone_low - zone_buffer) <= last_price <= (zone_high + zone_buffer)

    sl = float(impulse["low"]) if direction == "BUY" else float(impulse["high"])
    tp = (
        last_price + (impulse_range * 1.8)
        if direction == "BUY"
        else last_price - (impulse_range * 1.8)
    )
    parcial = last_price + (tp - last_price) * 0.35

    rr = _rr(last_price, sl, tp)
    sweep = detect_sweep(candles, side=direction, lookback=12)
    double_close_ok = _consecutive_closes_ok(candles, direction)
    followthrough_ok = _impulse_followthrough_ok(candles, direction)
    distance_ok = _distance_from_sweep_ok(candles, direction, last_price, sl)
    dead_zone_ok = _outside_dead_zone(last_price, zone_low, zone_high)

    context_ok = True
    timing_ok = inside_zone or double_close_ok or followthrough_ok
    structure_dirty = False
    late_entry = not near_zone
    spread_bad = False
    confluence_bonus = 0
    if near_zone:
        confluence_bonus += 1
    if double_close_ok:
        confluence_bonus += 1
    if followthrough_ok:
        confluence_bonus += 1
    if distance_ok:
        confluence_bonus += 1
    if dead_zone_ok:
        confluence_bonus += 1

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
    state = _resolve_state(
        score=score,
        inside_zone=inside_zone,
        near_zone=near_zone,
        sweep_valid=bool(sweep["valid"]),
        double_close_ok=double_close_ok,
        followthrough_ok=followthrough_ok,
        distance_ok=distance_ok,
        dead_zone_ok=dead_zone_ok,
    )
    setup_type = _setup_type(
        sweep_valid=bool(sweep["valid"]),
        double_close_ok=double_close_ok,
        followthrough_ok=followthrough_ok,
        inside_zone=inside_zone,
        near_zone=near_zone,
    )

    if state == "SIN_SETUP" and near_zone and score >= 7 and dead_zone_ok:
        state = "SET_UP"
        score = max(score, 7)

    if state == "SET_UP" and not dead_zone_ok:
        state = "SIN_SETUP"

    if state == "ENTRY" and not ((double_close_ok or followthrough_ok) and distance_ok and dead_zone_ok):
        state = "SET_UP"

    lots, risk_percent = calc_lots_from_score(
        symbol=symbol,
        entry=last_price,
        sl=sl,
        score=score if state == "ENTRY" else 0,
    )

    row = {
        "symbol": symbol,
        "tf": tf,
        "score": score,
        "state": state,
        "text": f"{direction} micro extendido" if state != "SIN_SETUP" else "SIN_SETUP",
        "action": direction if state in {"SET_UP", "ENTRY"} else "WAIT",
        "side": direction if state in {"SET_UP", "ENTRY"} else None,
        "entry": last_price if state in {"SET_UP", "ENTRY"} else None,
        "sl": sl if state in {"SET_UP", "ENTRY"} else None,
        "tp": tp if state in {"SET_UP", "ENTRY"} else None,
        "tp1": parcial if state in {"SET_UP", "ENTRY"} else None,
        "tp1_price": parcial if state in {"SET_UP", "ENTRY"} else None,
        "tp2": tp if state in {"SET_UP", "ENTRY"} else None,
        "parcial": parcial if state in {"SET_UP", "ENTRY"} else None,
        "lot": lots if state == "ENTRY" and lots > 0 else None,
        "risk_percent": risk_percent if state == "ENTRY" else 0.0,
        "rr": score_pack["rr"],
        "sweep_valid": sweep["valid"],
        "sweep_strength": sweep["strength"],
        "setup_type": setup_type,
        "zone_low": zone_low,
        "zone_high": zone_high,
        "candles": candles,
        "note": (
            f'{state} | score {score} | RR {score_pack["rr"]} | {sweep["reason"]}'
            f" | double_close={double_close_ok}"
            f" | followthrough={followthrough_ok}"
            f" | distance_ok={distance_ok}"
            f" | dead_zone_ok={dead_zone_ok}"
        ),
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
        "setup_type": setup_type,
        "zone_low": zone_low,
        "zone_high": zone_high,
    }

    return analysis, [row]
