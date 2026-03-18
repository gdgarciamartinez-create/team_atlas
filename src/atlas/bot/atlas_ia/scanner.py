from __future__ import annotations

from typing import Any, Dict, List, Tuple

STATE_PRIORITY = {
    "RUN": 70,
    "TP2": 60,
    "TP1": 50,
    "IN_TRADE": 40,
    "ENTRY": 30,
    "SET_UP": 20,
    "SIN_SETUP": 10,
    "CLOSED": 0,
}


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _normalize_state(state: Any) -> str:
    s = str(state or "").upper().strip()

    if s == "WAIT":
        return "SIN_SETUP"

    if s in {"WAIT_GATILLO", "SIGNAL", "SETUP"}:
        return "SET_UP"

    valid = {
        "SIN_SETUP",
        "SET_UP",
        "ENTRY",
        "IN_TRADE",
        "TP1",
        "TP2",
        "RUN",
        "CLOSED",
    }

    if s in valid:
        return s

    return "SIN_SETUP"


def _sort_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def key_fn(row: Dict[str, Any]):
        state = _normalize_state(row.get("state"))
        score = _safe_float(row.get("score"), 0.0)
        return (STATE_PRIORITY.get(state, 0), score)

    return sorted(rows, key=key_fn, reverse=True)


def _candles_of(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    candles = payload.get("candles", [])
    return candles if isinstance(candles, list) else []


def _body_ratio(candle: Dict[str, Any]) -> float:
    o = _safe_float(candle.get("o", candle.get("open")))
    h = _safe_float(candle.get("h", candle.get("high")))
    l = _safe_float(candle.get("l", candle.get("low")))
    c = _safe_float(candle.get("c", candle.get("close")))

    total = h - l
    body = abs(c - o)

    if total <= 0:
        return 0.0

    return body / total


def _range_strength(candles: List[Dict[str, Any]]) -> float:
    if len(candles) < 20:
        return 0.0

    recent = candles[-20:]
    highs = [_safe_float(c.get("h", c.get("high"))) for c in recent]
    lows = [_safe_float(c.get("l", c.get("low"))) for c in recent]

    highs = [x for x in highs if x > 0]
    lows = [x for x in lows if x > 0]

    if not highs or not lows:
        return 0.0

    hi = max(highs)
    lo = min(lows)
    if hi <= lo:
        return 0.0

    mid = (hi + lo) / 2.0
    if mid <= 0:
        return 0.0

    return (hi - lo) / mid


def _recent_body_confirmation(candles: List[Dict[str, Any]]) -> float:
    if len(candles) < 3:
        return 0.0

    last3 = candles[-3:]
    ratios = [_body_ratio(c) for c in last3]
    return sum(ratios) / len(ratios)


def _recent_displacement(candles: List[Dict[str, Any]]) -> float:
    if len(candles) < 6:
        return 0.0

    recent = candles[-6:]
    first_open = _safe_float(recent[0].get("o", recent[0].get("open")))
    last_close = _safe_float(recent[-1].get("c", recent[-1].get("close")))

    highs = [_safe_float(c.get("h", c.get("high"))) for c in recent]
    lows = [_safe_float(c.get("l", c.get("low"))) for c in recent]

    highs = [x for x in highs if x > 0]
    lows = [x for x in lows if x > 0]

    if not highs or not lows:
        return 0.0

    total_range = max(highs) - min(lows)
    if total_range <= 0:
        return 0.0

    move = abs(last_close - first_open)
    return move / total_range


def _is_dead_market_m1(candles: List[Dict[str, Any]]) -> bool:
    strength = _range_strength(candles)
    body_conf = _recent_body_confirmation(candles)
    disp = _recent_displacement(candles)

    if strength < 0.00035 and body_conf < 0.22 and disp < 0.28:
        return True

    return False


def _m1_quality_bonus(clean: Dict[str, Any], candles: List[Dict[str, Any]]) -> Dict[str, Any]:
    row = dict(clean)

    score = _safe_float(row.get("score"), 0.0)
    rr = _safe_float(row.get("rr"), 0.0)
    state = _normalize_state(row.get("state"))
    note = str(row.get("note") or "")

    strength = _range_strength(candles)
    body_conf = _recent_body_confirmation(candles)
    disp = _recent_displacement(candles)
    sweep_valid = bool(row.get("sweep_valid"))
    sweep_strength = _safe_float(row.get("sweep_strength"), 0.0)

    bonus = 0.0
    penalty = 0.0

    if sweep_valid:
        bonus += 0.5
    else:
        penalty += 0.75

    if sweep_strength >= 1.0:
        bonus += 0.5
    elif sweep_strength > 0 and sweep_strength < 0.45:
        penalty += 1.0
        note = f"{note} | weak_sweep".strip(" |")

    if rr >= 1.5:
        bonus += 0.5
    elif rr > 0 and rr < 1.15:
        penalty += 0.75

    if body_conf >= 0.45:
        bonus += 0.5
    elif body_conf < 0.18:
        penalty += 1.0
        note = f"{note} | weak_body".strip(" |")

    if disp >= 0.55:
        bonus += 0.75
    elif disp < 0.22:
        penalty += 1.25
        note = f"{note} | weak_displacement".strip(" |")

    if strength < 0.00025:
        penalty += 1.5
        note = f"{note} | low_range_m1".strip(" |")
    elif strength < 0.00035:
        penalty += 0.75

    new_score = max(0.0, score + bonus - penalty)
    row["score"] = round(new_score, 2)

    if state in {"SET_UP", "ENTRY"} and _is_dead_market_m1(candles):
        row["state"] = "SIN_SETUP"
        row["note"] = f"{note} | filtro_m1_dead_market".strip(" |")
        return row

    has_plan = row.get("entry") is not None and row.get("sl") is not None and row.get("tp") is not None
    if state == "SIN_SETUP" and has_plan and new_score >= 9.0 and not _is_dead_market_m1(candles):
        row["state"] = "SET_UP"
        if row.get("side") is None:
            action = row.get("action")
            row["side"] = action if action in {"BUY", "SELL"} else None

    row["note"] = note
    return row


def _relax_row_for_mode(row: Dict[str, Any], atlas_mode: str, candles: List[Dict[str, Any]]) -> Dict[str, Any]:
    clean = dict(row)
    state = _normalize_state(clean.get("state"))
    score = _safe_float(clean.get("score"), 0.0)
    rr = _safe_float(clean.get("rr"), 0.0)
    sweep_valid = bool(clean.get("sweep_valid"))
    side = clean.get("side")
    entry = clean.get("entry")
    sl = clean.get("sl")
    tp = clean.get("tp")

    has_plan = entry is not None and sl is not None and tp is not None
    mode = str(atlas_mode or "").upper().strip()

    if mode == "SCALPING_M1":
        clean = _m1_quality_bonus(clean, candles)
        state = _normalize_state(clean.get("state"))
        score = _safe_float(clean.get("score"), 0.0)

        if state == "SIN_SETUP" and has_plan and score >= 9.0 and not _is_dead_market_m1(candles):
            clean["state"] = "SET_UP"
            if side is None:
                action = clean.get("action")
                clean["side"] = action if action in {"BUY", "SELL"} else None

    elif mode == "SCALPING_M5":
        if state == "SIN_SETUP" and has_plan and score >= 8 and sweep_valid:
            clean["state"] = "SET_UP"
            if side is None:
                action = clean.get("action")
                clean["side"] = action if action in {"BUY", "SELL"} else None

    elif mode == "FOREX":
        if state == "SIN_SETUP" and has_plan and score >= 8 and rr >= 1.3 and sweep_valid:
            clean["state"] = "SET_UP"
            if score < 8:
                clean["score"] = 8

    return clean


def _run_mode_for_symbol(
    atlas_mode: str,
    symbol: str,
    candles: List[Dict[str, Any]],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    mode = str(atlas_mode or "").upper().strip()

    if mode == "SCALPING_M1":
        from atlas.bot.atlas_ia_m1.engine import run_world_rows
        return run_world_rows(
            world="ATLAS_IA",
            tf="M1",
            symbols=[symbol],
            candles_by_symbol={symbol: {"candles": candles}},
        )

    if mode == "SCALPING_M5":
        from atlas.bot.atlas_ia_m5.engine import run_world_rows
        return run_world_rows(
            world="ATLAS_IA",
            tf="M5",
            symbols=[symbol],
            candles_by_symbol={symbol: {"candles": candles}},
        )

    from atlas.bot.atlas_ia.forex_engine import eval_forex
    analysis, ui = eval_forex(
        {"symbol": symbol, "candles": candles},
        {"symbol": symbol, "tf": "H1"},
    )

    rows: List[Dict[str, Any]] = []
    if isinstance(ui, dict):
        maybe_rows = ui.get("rows", [])
        if isinstance(maybe_rows, list):
            rows = maybe_rows

    return analysis, rows


def scan_opportunities(
    atlas_mode: str,
    candles_by_symbol: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    analyses: List[Dict[str, Any]] = []
    mode = str(atlas_mode or "").upper().strip()

    for symbol, payload in candles_by_symbol.items():
        try:
            candles = _candles_of(payload)
            analysis, raw_rows = _run_mode_for_symbol(mode, symbol, candles)

            if isinstance(analysis, dict):
                analyses.append(analysis)
            else:
                analyses.append({"symbol": symbol})

            if not isinstance(raw_rows, list):
                raw_rows = []

            for row in raw_rows:
                if not isinstance(row, dict):
                    continue

                clean_row = dict(row)
                clean_row["symbol"] = clean_row.get("symbol") or symbol
                clean_row["state"] = _normalize_state(clean_row.get("state"))
                clean_row["score"] = _safe_float(clean_row.get("score"), 0.0)

                if "tf" not in clean_row or not clean_row.get("tf"):
                    if mode == "SCALPING_M1":
                        clean_row["tf"] = "M1"
                    elif mode == "SCALPING_M5":
                        clean_row["tf"] = "M5"
                    else:
                        clean_row["tf"] = "H1"

                clean_row = _relax_row_for_mode(clean_row, mode, candles)
                rows.append(clean_row)

        except Exception as e:
            rows.append({
                "symbol": symbol,
                "tf": "M1" if mode == "SCALPING_M1" else "M5" if mode == "SCALPING_M5" else "H1",
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
                "sweep_valid": False,
                "sweep_strength": 0.0,
                "note": f"scanner_error: {repr(e)}",
            })

    sorted_rows = _sort_rows(rows)

    top_entry = next((r for r in sorted_rows if _normalize_state(r.get("state")) == "ENTRY"), None)
    top_setup = next((r for r in sorted_rows if _normalize_state(r.get("state")) == "SET_UP"), None)
    top_live = next(
        (r for r in sorted_rows if _normalize_state(r.get("state")) in {"IN_TRADE", "TP1", "TP2", "RUN"}),
        None,
    )

    summary = {
        "mode": mode,
        "total_symbols": len(candles_by_symbol),
        "total_rows": len(sorted_rows),
        "entries": sum(1 for r in sorted_rows if _normalize_state(r.get("state")) == "ENTRY"),
        "setups": sum(1 for r in sorted_rows if _normalize_state(r.get("state")) == "SET_UP"),
        "live": sum(1 for r in sorted_rows if _normalize_state(r.get("state")) in {"IN_TRADE", "TP1", "TP2", "RUN"}),
        "top_entry": top_entry,
        "top_setup": top_setup,
        "top_live": top_live,
    }

    return {
        "ok": True,
        "summary": summary,
        "rows": sorted_rows,
        "analyses": analyses,
    }
