from __future__ import annotations

from typing import Any, Dict, List, Optional

from atlas.api.risk import calc_lots_from_score
from atlas.bot.analysis.scoring import calc_score
from atlas.bot.analysis.sweep import detect_sweep


def _safe_price(candle: Dict[str, Any], key_main: str, key_alt: str):
    v = candle.get(key_main, candle.get(key_alt))
    try:
        return float(v)
    except Exception:
        return None


def _normalize_candles(md: Dict[str, Any]) -> List[Dict[str, float]]:
    src = md.get("candles", [])
    out: List[Dict[str, float]] = []

    if not isinstance(src, list):
        return out

    for c in src:
        o = _safe_price(c, "open", "o")
        h = _safe_price(c, "high", "h")
        l = _safe_price(c, "low", "l")
        cl = _safe_price(c, "close", "c")

        if None in (o, h, l, cl):
            continue

        item: Dict[str, float] = {"o": o, "h": h, "l": l, "c": cl}
        t = c.get("time", c.get("t"))
        if t is not None:
            item["t"] = t

        out.append(item)

    return out


def _last_swing(candles: List[Dict[str, float]]):
    if len(candles) < 48:
        return None

    windows = [24, 32, 48]
    best_swing: Optional[Dict[str, float | int | str]] = None
    best_range = -1.0

    for w in windows:
        window = candles[-w:]
        high = max(c["h"] for c in window)
        low = min(c["l"] for c in window)

        if high == low:
            continue

        rng = abs(high - low)
        direction = "BUY" if candles[-1]["c"] > candles[-max(2, w // 2)]["c"] else "SELL"

        score = rng
        if score > best_range:
            best_range = score
            best_swing = {
                "high": high,
                "low": low,
                "dir": direction,
                "range": rng,
                "window": w,
            }

    return best_swing


def _fib_zone(swing):
    high = float(swing["high"])
    low = float(swing["low"])
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
        "tp1": None,
        "tp1_price": None,
        "tp2": None,
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


def _body_ratio(candle: Dict[str, float]) -> float:
    total = float(candle["h"]) - float(candle["l"])
    body = abs(float(candle["c"]) - float(candle["o"]))
    if total <= 0:
        return 0.0
    return body / total


def _recent_displacement(candles: List[Dict[str, float]], n: int = 8) -> float:
    if len(candles) < n:
        return 0.0

    recent = candles[-n:]
    first_open = float(recent[0]["o"])
    last_close = float(recent[-1]["c"])
    highs = [float(c["h"]) for c in recent]
    lows = [float(c["l"]) for c in recent]

    total_range = max(highs) - min(lows)
    if total_range <= 0:
        return 0.0

    move = abs(last_close - first_open)
    return move / total_range


def _flip_count(candles: List[Dict[str, float]], n: int = 8) -> int:
    if len(candles) < n:
        return 99

    recent = candles[-n:]
    dirs: List[int] = []
    for c in recent:
        dirs.append(1 if float(c["c"]) >= float(c["o"]) else -1)

    flips = 0
    for i in range(1, len(dirs)):
        if dirs[i] != dirs[i - 1]:
            flips += 1
    return flips


def _directional_close_ok(candles: List[Dict[str, float]], side: str) -> bool:
    if not candles:
        return False
    last = candles[-1]
    if side == "BUY":
        return float(last["c"]) > float(last["o"])
    return float(last["c"]) < float(last["o"])


def _followthrough_ok(candles: List[Dict[str, float]], side: str) -> bool:
    if len(candles) < 4:
        return False

    closes = [float(c["c"]) for c in candles[-4:]]
    if side == "BUY":
        return sum(1 for i in range(1, len(closes)) if closes[i] >= closes[i - 1]) >= 2
    return sum(1 for i in range(1, len(closes)) if closes[i] <= closes[i - 1]) >= 2


def _structure_clean_ok(candles: List[Dict[str, float]]) -> bool:
    if len(candles) < 8:
        return False
    body_conf = sum(_body_ratio(c) for c in candles[-3:]) / 3.0
    disp = _recent_displacement(candles, n=8)
    flips = _flip_count(candles, n=8)
    return body_conf >= 0.14 and disp >= 0.10 and flips <= 7


def _resolve_state(
    score: int,
    inside_zone: bool,
    near_zone: bool,
    sweep_valid: bool,
    structure_clean: bool,
    directional_close: bool,
    followthrough_ok: bool,
) -> str:
    strong_context = structure_clean and (directional_close or followthrough_ok)

    if inside_zone and score >= 7 and strong_context and (sweep_valid or directional_close or followthrough_ok):
        return "ENTRY"

    if inside_zone and score >= 5 and structure_clean and (directional_close or followthrough_ok):
        return "SET_UP"

    if inside_zone and score >= 4 and (structure_clean or directional_close or followthrough_ok):
        return "SET_UP"

    if near_zone and score >= 5 and structure_clean and (directional_close or followthrough_ok):
        return "SET_UP"

    if near_zone and score >= 4 and structure_clean:
        return "SET_UP"

    if near_zone and score >= 3 and (directional_close or followthrough_ok):
        return "SET_UP"

    return "SIN_SETUP"


def _setup_type(
    sweep_valid: bool,
    inside_zone: bool,
    near_zone: bool,
    structure_clean: bool,
    followthrough_ok: bool,
) -> str:
    if sweep_valid and (inside_zone or near_zone):
        return "forex_sweep_reclaim"
    if inside_zone and followthrough_ok:
        return "forex_inside_zone_followthrough"
    if structure_clean:
        return "forex_clean_pullback"
    return "forex_clean_pullback"


def _recent_zone_extreme(candles: List[Dict[str, float]], side: str, n: int = 6) -> float | None:
    if len(candles) < n:
        return None

    recent = candles[-n:]
    if side == "BUY":
        return min(float(c["l"]) for c in recent)
    return max(float(c["h"]) for c in recent)


def _build_technical_sl(
    candles: List[Dict[str, float]],
    direction: str,
    z_low: float,
    z_high: float,
    swing_low: float,
    swing_high: float,
    swing_range: float,
) -> float:
    zone_size = abs(z_high - z_low)
    recent_extreme = _recent_zone_extreme(candles, direction, n=6)

    buffer_zone = zone_size * 0.22
    buffer_swing = swing_range * 0.05
    buffer = max(buffer_zone, buffer_swing)

    if direction == "BUY":
        candidates = [z_low - buffer]
        if recent_extreme is not None:
            candidates.append(recent_extreme - buffer_swing)
        sl = min(candidates)
        hard_floor = swing_low - (swing_range * 0.02)
        return max(sl, hard_floor)

    candidates = [z_high + buffer]
    if recent_extreme is not None:
        candidates.append(recent_extreme + buffer_swing)
    sl = max(candidates)
    hard_cap = swing_high + (swing_range * 0.02)
    return min(sl, hard_cap)


def _tp2_target(direction: str, swing_high: float, swing_low: float) -> float:
    return swing_high if direction == "BUY" else swing_low


def _tp1_target(entry: float, tp2: float, side: str) -> float:
    if side == "BUY":
        return entry + ((tp2 - entry) * 0.60)
    return entry - ((entry - tp2) * 0.60)


def _minimum_rr_ok(entry: float, sl: float, tp2: float, min_rr: float = 1.35) -> bool:
    return _rr(entry, sl, tp2) >= min_rr


def eval_forex(md: Dict[str, Any], raw_query: Dict[str, Any]):
    symbol = raw_query.get("symbol") or md.get("symbol") or "EURUSDz"
    tf = raw_query.get("tf") or "H1"

    candles = _normalize_candles(md)

    if len(candles) < 48:
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
    last_price = float(candles[-1]["c"])
    direction = str(swing["dir"])
    swing_range = float(swing["range"])
    swing_window = int(swing.get("window", 0))
    zone_buffer = swing_range * 0.35

    sl = _build_technical_sl(
        candles=candles,
        direction=direction,
        z_low=float(z_low),
        z_high=float(z_high),
        swing_low=float(swing["low"]),
        swing_high=float(swing["high"]),
        swing_range=swing_range,
    )

    tp2 = _tp2_target(direction, float(swing["high"]), float(swing["low"]))
    tp1 = _tp1_target(last_price, tp2, direction)
    parcial = tp1

    rr = _rr(last_price, sl, tp2)
    sweep = detect_sweep(candles, side=direction, lookback=14)

    inside_zone = z_low <= last_price <= z_high
    near_zone = (z_low - zone_buffer) <= last_price <= (z_high + zone_buffer)

    structure_clean = _structure_clean_ok(candles)
    directional_close = _directional_close_ok(candles, direction)
    follow_ok = _followthrough_ok(candles, direction)
    rr_ok = _minimum_rr_ok(last_price, sl, tp2, min_rr=1.35)

    flips = _flip_count(candles, n=8)
    displacement = _recent_displacement(candles, n=8)

    score_pack = calc_score(
        side=direction,
        entry=last_price,
        sl=sl,
        tp=tp2,
        sweep=sweep,
        context_ok=structure_clean or directional_close or follow_ok,
        timing_ok=(
            inside_zone
            or (near_zone and structure_clean)
            or (near_zone and directional_close)
            or (near_zone and follow_ok)
            or (near_zone and bool(sweep["valid"]))
        ),
        zone_touch_count=1,
        late_entry=not inside_zone,
        structure_dirty=not structure_clean,
        spread_bad=False,
        confluence_bonus=(
            (1 if inside_zone else 0)
            + (1 if near_zone else 0)
            + (1 if sweep["valid"] else 0)
            + (1 if directional_close else 0)
            + (1 if follow_ok else 0)
            + (1 if rr_ok else 0)
        ),
    )

    score = int(score_pack["score"])
    state = _resolve_state(
        score,
        inside_zone,
        near_zone,
        bool(sweep["valid"]),
        structure_clean,
        directional_close,
        follow_ok,
    )
    setup_type = _setup_type(
        sweep_valid=bool(sweep["valid"]),
        inside_zone=inside_zone,
        near_zone=near_zone,
        structure_clean=structure_clean,
        followthrough_ok=follow_ok,
    )

    if state == "SIN_SETUP" and near_zone and score >= 3 and (structure_clean or directional_close or follow_ok):
        state = "SET_UP"
        score = max(score, 3)

    if state == "SIN_SETUP" and inside_zone and score >= 4 and (structure_clean or directional_close or follow_ok):
        state = "SET_UP"
        score = max(score, 4)

    if state in {"SET_UP", "ENTRY"} and not rr_ok:
        state = "SIN_SETUP"

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
        "tp": tp2 if state != "SIN_SETUP" else None,
        "tp1": tp1 if state != "SIN_SETUP" else None,
        "tp1_price": tp1 if state != "SIN_SETUP" else None,
        "tp2": tp2 if state != "SIN_SETUP" else None,
        "parcial": parcial if state != "SIN_SETUP" else None,
        "lot": lots if state == "ENTRY" else None,
        "risk_percent": risk_percent if state == "ENTRY" else 0.0,
        "rr": rr,
        "zone_low": z_low,
        "zone_high": z_high,
        "sweep_valid": sweep["valid"],
        "sweep_strength": sweep["strength"],
        "setup_type": setup_type,
        "swing_window": swing_window,
        "candles": candles,
        "note": (
            f"{state} | score {score} | RR {rr:.2f} | {sweep['reason']}"
            f" | structure_clean={structure_clean}"
            f" | dir_close={directional_close}"
            f" | followthrough={follow_ok}"
            f" | rr_ok={rr_ok}"
            f" | window={swing_window}"
            f" | flips={flips}"
            f" | disp={displacement:.2f}"
        ),
    }

    analysis = {
        "world": "ATLAS_IA",
        "atlas_mode": "FOREX",
        "status": state,
        "signals": 1 if state in {"SET_UP", "ENTRY"} else 0,
        "reason": row["note"],
        "score": score,
        "side": direction,
        "setup_type": setup_type,
        "zone_low": z_low,
        "zone_high": z_high,
        "swing_window": swing_window,
    }

    return analysis, {"rows": [row]}