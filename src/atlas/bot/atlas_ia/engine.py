from __future__ import annotations

from typing import Any, Dict, List, Tuple


def _safe_price(candle: Dict[str, Any], key_main: str, key_alt: str) -> float | None:
    value = candle.get(key_main, candle.get(key_alt))
    try:
        return float(value)
    except Exception:
        return None


def _normalize_candles(md: Dict[str, Any]) -> List[Dict[str, float]]:
    src = md.get("candles", [])
    out: List[Dict[str, float]] = []

    if not isinstance(src, list):
        return out

    for c in src:
        if not isinstance(c, dict):
            continue

        o = _safe_price(c, "open", "o")
        h = _safe_price(c, "high", "h")
        l = _safe_price(c, "low", "l")
        cl = _safe_price(c, "close", "c")

        if o is None or h is None or l is None or cl is None:
            continue

        row: Dict[str, float] = {"o": o, "h": h, "l": l, "c": cl}
        t = c.get("time", c.get("t"))
        if t is not None:
            row["t"] = t

        out.append(row)

    return out


def _build_wait_row(symbol: str, tf: str, score: int = 0, note: str = "SIN_SETUP") -> Dict[str, Any]:
    return {
        "symbol": symbol,
        "tf": tf,
        "score": score,
        "state": "SIN_SETUP",
        "side": None,
        "entry": None,
        "sl": None,
        "tp": None,
        "parcial": None,
        "lot": None,
        "risk_percent": 0.0,
        "rr": 0.0,
        "note": note,
        "zone_low": None,
        "zone_high": None,
        "sweep_valid": False,
        "sweep_strength": 0.0,
    }


def _normalize_engine_rows(rows: List[Dict[str, Any]], symbol: str, tf: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []

    for row in rows:
        if not isinstance(row, dict):
            continue

        entry = row.get("entry")
        sl = row.get("sl")
        tp = row.get("tp")

        state = str(row.get("state") or "").upper().strip()

        if state == "WAIT":
            state = "SIN_SETUP"
        elif state in {"WAIT_GATILLO", "SIGNAL", "SETUP"}:
            state = "SET_UP"

        valid_states = {
            "SIN_SETUP",
            "SET_UP",
            "ENTRY",
            "IN_TRADE",
            "TP1",
            "TP2",
            "RUN",
            "CLOSED",
        }

        if state not in valid_states:
            state = "SET_UP" if entry is not None and sl is not None and tp is not None else "SIN_SETUP"

        parcial = row.get("parcial")
        if parcial is None:
            parcial = row.get("partial")
        if parcial is None:
            parcial = row.get("tp1")
        if parcial is None and entry is not None and tp is not None:
            try:
                parcial = (float(entry) + float(tp)) / 2.0
            except Exception:
                parcial = None

        out.append({
            "symbol": row.get("symbol") or symbol,
            "tf": row.get("tf") or tf,
            "score": row.get("score", 0),
            "state": state,
            "side": row.get("side"),
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "parcial": parcial,
            "lot": row.get("lot"),
            "risk_percent": row.get("risk_percent"),
            "rr": row.get("rr"),
            "note": row.get("text") or row.get("note"),
            "candles": row.get("candles"),
            "signal_ts": row.get("signal_ts"),
            "signal_candle_time": row.get("signal_candle_time"),
            "entry_ts": row.get("entry_ts"),
            "entry_candle_time": row.get("entry_candle_time"),
            "tp1_ts": row.get("tp1_ts"),
            "tp2_ts": row.get("tp2_ts"),
            "run_ts": row.get("run_ts"),
            "closed_ts": row.get("closed_ts"),
            "close_reason": row.get("close_reason"),
            "close_price": row.get("close_price"),
            "zone_low": row.get("zone_low"),
            "zone_high": row.get("zone_high"),
            "sweep_valid": row.get("sweep_valid"),
            "sweep_strength": row.get("sweep_strength"),
        })

    return out


def _run_scalping_m1(symbol: str, tf: str, md: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    from atlas.bot.atlas_ia_m1.engine import run_world_rows

    analysis, rows = run_world_rows(
        world="ATLAS_IA",
        tf=tf,
        symbols=[symbol],
        candles_by_symbol={symbol: {"candles": _normalize_candles(md)}},
    )
    return analysis, _normalize_engine_rows(rows, symbol, tf)


def _run_scalping_m5(symbol: str, tf: str, md: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    from atlas.bot.atlas_ia_m5.engine import run_world_rows

    analysis, rows = run_world_rows(
        world="ATLAS_IA",
        tf=tf,
        symbols=[symbol],
        candles_by_symbol={symbol: {"candles": _normalize_candles(md)}},
    )
    return analysis, _normalize_engine_rows(rows, symbol, tf)


def _run_forex(symbol: str, tf: str, md: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    from atlas.bot.atlas_ia.forex_engine import eval_forex

    analysis, ui = eval_forex(md, {"symbol": symbol, "tf": tf})

    rows: List[Dict[str, Any]] = []
    if isinstance(ui, dict):
        raw_rows = ui.get("rows", [])
        if isinstance(raw_rows, list):
            rows = raw_rows

    return analysis, _normalize_engine_rows(rows, symbol, tf)


def eval_atlas_ia(md: Dict[str, Any], raw_query: Dict[str, Any] | None = None):
    raw_query = raw_query or {}

    symbol = raw_query.get("symbol") or md.get("symbol") or "XAUUSDz"
    atlas_mode = str(raw_query.get("atlas_mode") or "SCALPING_M1").upper().strip()

    if atlas_mode == "SCALPING_M1":
        tf = "M1"
    elif atlas_mode == "SCALPING_M5":
        tf = "M5"
    else:
        tf = "H1"

    candles = _normalize_candles(md)
    if len(candles) == 0:
        analysis = {
            "world": "ATLAS_IA",
            "atlas_mode": atlas_mode,
            "status": "NO_DATA",
            "reason": "No candles in payload",
        }
        ui = {"rows": [_build_wait_row(symbol, tf, 0, "Sin velas")]}
        return analysis, ui

    if atlas_mode == "SCALPING_M1":
        analysis, rows = _run_scalping_m1(symbol, tf, md)
    elif atlas_mode == "SCALPING_M5":
        analysis, rows = _run_scalping_m5(symbol, tf, md)
    elif atlas_mode == "FOREX":
        analysis, rows = _run_forex(symbol, tf, md)
    else:
        analysis = {
            "world": "ATLAS_IA",
            "atlas_mode": atlas_mode,
            "status": "UNKNOWN_MODE",
            "reason": f"Unknown atlas_mode: {atlas_mode}",
        }
        rows = [_build_wait_row(symbol, tf, 0, "Modo desconocido")]

    analysis = {
        "world": "ATLAS_IA",
        "atlas_mode": atlas_mode,
        **analysis,
    }

    ui = {"rows": rows}
    return analysis, ui