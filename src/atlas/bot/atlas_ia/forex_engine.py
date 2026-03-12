from __future__ import annotations

from typing import Any, Dict, List, Tuple

from atlas.api.risk import calc_lots_from_score
from atlas.bot.analysis.sweep import detect_sweep
from atlas.bot.analysis.scoring import calc_score


def _safe_price(candle: Dict[str, Any], key_main: str, key_alt: str):
    v = candle.get(key_main, candle.get(key_alt))
    try:
        return float(v)
    except Exception:
        return None


def _normalize_candles(md: Dict[str, Any]) -> List[Dict[str, float]]:
    src = md.get("candles", [])
    out = []

    if not isinstance(src, list):
        return out

    for c in src:
        o = _safe_price(c, "open", "o")
        h = _safe_price(c, "high", "h")
        l = _safe_price(c, "low", "l")
        cl = _safe_price(c, "close", "c")

        if None in (o, h, l, cl):
            continue

        item = {"o": o, "h": h, "l": l, "c": cl}
        t = c.get("time", c.get("t"))
        if t is not None:
            item["t"] = t

        out.append(item)

    return out


def _last_swing(candles: List[Dict[str, float]]):
    if len(candles) < 40:
        return None

    window = candles[-40:]
    high = max(c["h"] for c in window)
    low = min(c["l"] for c in window)

    if high == low:
        return None

    direction = "BUY" if candles[-1]["c"] > candles[-20]["c"] else "SELL"

    return {
        "high": high,
        "low": low,
        "dir": direction,
        "range": abs(high - low),
    }


def _fib_zone(swing):
    high = swing["high"]
    low = swing["low"]
    direction = swing["dir"]

    if direction == "BUY":
        fib618 = high - (high - low) * 0.618
        fib786 = high - (high - low) * 0.786
        return min(fib618, fib786), max(fib618, fib786)

    fib618 = low + (high - low) * 0.618
    fib786 = low + (high - low) * 0.786
    return min(fib618, fib786), max(fib618, fib786)


def _rr(entry, sl, tp):
    risk = abs(entry - sl)
    reward = abs(tp - entry)
    if risk <= 0:
        return 0.0
    return reward / risk


def _wait_row(symbol, tf, note):
    return {
        "symbol": symbol,
        "tf": tf,
        "score": 0,
        "state": "SIN_SETUP",
        "side": None,
        "entry": None,
        "sl": None,
        "tp": None,
        "parcial": None,
        "lot": None,
        "risk_percent": 0.0,
        "rr": 0.0,
        "zone_low": None,
        "zone_high": None,
        "sweep_valid": False,
        "sweep_strength": 0.0,
        "note": note,
    }


def _resolve_state(score: int, inside_zone: bool, near_zone: bool, sweep_valid: bool) -> str:
    if inside_zone and sweep_valid and score >= 9:
        return "ENTRY"
    if inside_zone and score >= 8:
        return "SET_UP"
    if near_zone and score >= 7:
        return "SET_UP"
    return "SIN_SETUP"


def eval_forex(md: Dict[str, Any], raw_query: Dict[str, Any]):
    symbol = raw_query.get("symbol") or md.get("symbol") or "EURUSDz"
    tf = raw_query.get("tf") or "H1"

    candles = _normalize_candles(md)

    if len(candles) < 40:
        analysis = {
            "world": "ATLAS_IA",
            "atlas_mode": "FOREX",
            "status": "SIN_SETUP",
            "signals": 0,
            "reason": "No hay velas suficientes",
        }
        return analysis, {"rows": [_wait_row(symbol, tf, "Sin velas")]}

    swing = _last_swing(candles)
    if not swing:
        analysis = {
            "world": "ATLAS_IA",
            "atlas_mode": "FOREX",
            "status": "SIN_SETUP",
            "signals": 0,
            "reason": "Sin swing H1",
        }
        return analysis, {"rows": [_wait_row(symbol, tf, "Sin swing H1")]}

    z_low, z_high = _fib_zone(swing)
    last_price = candles[-1]["c"]
    direction = swing["dir"]
    swing_range = float(swing["range"])
    zone_buffer = swing_range * 0.10

    sl = swing["low"] if direction == "BUY" else swing["high"]
    tp = swing["high"] if direction == "BUY" else swing["low"]
    parcial = last_price + (tp - last_price) * 0.5

    rr = _rr(last_price, sl, tp)
    sweep = detect_sweep(candles, side=direction, lookback=14)

    inside_zone = z_low <= last_price <= z_high
    near_zone = (z_low - zone_buffer) <= last_price <= (z_high + zone_buffer)

    score_pack = calc_score(
        side=direction,
        entry=last_price,
        sl=sl,
        tp=tp,
        sweep=sweep,
        context_ok=True,
        timing_ok=inside_zone or near_zone,
        zone_touch_count=1,
        late_entry=not near_zone,
        structure_dirty=False,
        spread_bad=False,
        confluence_bonus=1 if near_zone else 0,
    )

    score = int(score_pack["score"])
    state = _resolve_state(score, inside_zone, near_zone, bool(sweep["valid"]))

    if state == "SIN_SETUP" and near_zone and score >= 6:
        state = "SET_UP"
        score = max(score, 7)

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
        "side": direction if state != "SIN_SETUP" else None,
        "entry": last_price if state != "SIN_SETUP" else None,
        "sl": sl if state != "SIN_SETUP" else None,
        "tp": tp if state != "SIN_SETUP" else None,
        "parcial": parcial if state != "SIN_SETUP" else None,
        "lot": lots if state == "ENTRY" else None,
        "risk_percent": risk_percent if state == "ENTRY" else 0.0,
        "rr": score_pack["rr"],
        "zone_low": z_low,
        "zone_high": z_high,
        "sweep_valid": sweep["valid"],
        "sweep_strength": sweep["strength"],
        "candles": candles,
        "note": f"{state} · score {score} · RR {score_pack['rr']} · {sweep['reason']}",
    }

    analysis = {
        "world": "ATLAS_IA",
        "atlas_mode": "FOREX",
        "status": state,
        "signals": 1 if state in {"SET_UP", "ENTRY"} else 0,
        "reason": row["note"],
        "score": score,
        "side": direction,
        "zone_low": z_low,
        "zone_high": z_high,
    }

    return analysis, {"rows": [row]}