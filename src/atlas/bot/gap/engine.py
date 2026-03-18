from __future__ import annotations

import os
from datetime import datetime, time as dtime
from typing import Any, Dict, Tuple
from zoneinfo import ZoneInfo

from atlas.config import settings


TZ = ZoneInfo("America/Santiago")


def _season() -> str:
    s = (os.getenv("ATLAS_CHILE_SEASON") or "SUMMER").upper().strip()
    return "WINTER" if s == "WINTER" else "SUMMER"


def _window_for(season: str) -> Tuple[dtime, dtime]:
    if season == "WINTER":
        return dtime(18, 55), dtime(19, 30)
    return dtime(19, 55), dtime(20, 30)


def _in_window(now: datetime, start: dtime, end: dtime) -> bool:
    nt = now.time()
    return (nt >= start) and (nt <= end)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _norm_symbol(symbol: str) -> str:
    return str(symbol or "").strip().upper()


def _row(
    symbol: str,
    tf: str,
    side: str,
    state: str,
    entry: float,
    sl: float,
    tp: float,
    score: int,
    note: str,
    setup_type: str = "gap_extension_failure",
) -> Dict[str, Any]:
    return {
        "symbol": symbol,
        "tf": tf,
        "world": "GAP",
        "atlas_mode": "GAP",
        "side": side,
        "state": state,
        "entry": float(entry),
        "sl": float(sl),
        "tp": float(tp),
        "score": int(score),
        "setup_type": setup_type,
        "note": note,
    }


def eval_gap(md: Dict[str, Any], raw_query: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    season = _season()
    start, end = _window_for(season)
    now = datetime.now(TZ)

    symbol = str(raw_query.get("symbol") or "")
    tf = str(raw_query.get("tf") or "M1").upper().strip()
    candles = md.get("candles") or []
    price = _safe_float(md.get("price"), 0.0)

    wait_row = _row(
        symbol=symbol,
        tf=tf,
        side="WAIT",
        state="WAIT",
        entry=0.0,
        sl=0.0,
        tp=0.0,
        score=0,
        note="GAP waiting",
        setup_type="gap_extension_failure",
    )

    if not _in_window(now, start, end):
        analysis = {
            "world": "GAP",
            "status": "SLEEP",
            "state": "WAIT",
            "reason": "OUT_OF_GAP_WINDOW",
            "note": "Fuera de ventana GAP",
        }
        wait_row["note"] = "Fuera de ventana GAP"
        return analysis, {"rows": [wait_row]}

    if _norm_symbol(symbol) not in {"XAUUSD", "XAUUSDZ"}:
        analysis = {
            "world": "GAP",
            "status": "OK",
            "state": "WAIT",
            "reason": "NOT_GOLD",
            "note": "GAP solo opera XAUUSD/XAUUSDz",
        }
        wait_row["note"] = "GAP solo opera XAUUSD/XAUUSDz"
        return analysis, {"rows": [wait_row]}

    if len(candles) < 3 or price <= 0:
        analysis = {
            "world": "GAP",
            "status": "OK",
            "state": "WAIT",
            "reason": "NO_DATA",
            "note": "GAP sin velas suficientes",
        }
        wait_row["note"] = "GAP sin velas suficientes"
        return analysis, {"rows": [wait_row]}

    prev = candles[-2]
    curr = candles[-1]
    prev_close = _safe_float(prev.get("c", prev.get("close")), 0.0)
    curr_open = _safe_float(curr.get("o", curr.get("open")), 0.0)
    curr_high = _safe_float(curr.get("h", curr.get("high")), 0.0)
    curr_low = _safe_float(curr.get("l", curr.get("low")), 0.0)
    curr_close = _safe_float(curr.get("c", curr.get("close")), 0.0)

    gap = curr_open - prev_close
    ref_price = abs(curr_close) or abs(curr_open) or 1.0
    gap_threshold = _safe_float(getattr(settings, "gap_threshold", 0.0015), 0.0015)

    if abs(gap) / ref_price < gap_threshold:
        analysis = {
            "world": "GAP",
            "status": "OK",
            "state": "WAIT",
            "reason": "NO_GAP",
            "note": "GAP no valido",
        }
        wait_row["note"] = "GAP no valido"
        return analysis, {"rows": [wait_row]}

    side = "SELL" if gap > 0 else "BUY"
    gap_low = min(prev_close, curr_open)
    gap_high = max(prev_close, curr_open)

    if side == "SELL":
        extension = curr_high > gap_high
        failed_continuity = curr_close < curr_open
        recovery = curr_close <= gap_high
        entry = curr_close
        sl = curr_high
        tp = gap_low
    else:
        extension = curr_low < gap_low
        failed_continuity = curr_close > curr_open
        recovery = curr_close >= gap_low
        entry = curr_close
        sl = curr_low
        tp = gap_high

    if not extension:
        analysis = {
            "world": "GAP",
            "status": "OK",
            "state": "WAIT",
            "reason": "WAIT_EXTENSION",
            "note": "GAP esperando extension/exageracion",
        }
        wait_row["note"] = "GAP esperando extension/exageracion"
        return analysis, {"rows": [wait_row]}

    if not failed_continuity:
        analysis = {
            "world": "GAP",
            "status": "OK",
            "state": "WAIT",
            "reason": "CONTINUITY_ALIVE",
            "note": "GAP con continuidad aun viva",
        }
        wait_row["note"] = "GAP con continuidad aun viva"
        return analysis, {"rows": [wait_row]}

    if not recovery:
        row = _row(
            symbol=symbol,
            tf=tf,
            side=side,
            state="SET_UP",
            entry=entry,
            sl=sl,
            tp=tp,
            score=8,
            setup_type="gap_extension_failure",
            note="GAP set-up: exageracion -> fallo, faltando recuperacion",
        )
        analysis = {
            "world": "GAP",
            "status": "OK",
            "state": "SET_UP",
            "reason": "WAIT_RECOVERY",
            "setup_type": "gap_extension_failure",
            "note": row["note"],
        }
        return analysis, {"rows": [row]}

    row = _row(
        symbol=symbol,
        tf=tf,
        side=side,
        state="ENTRY",
        entry=entry,
        sl=sl,
        tp=tp,
        score=9,
        setup_type="gap_failure_recovery",
        note="GAP entry: exageracion -> fallo -> recuperacion",
    )
    analysis = {
        "world": "GAP",
        "status": "OK",
        "state": "ENTRY",
        "reason": "RECOVERY_CONFIRMED",
        "setup_type": "gap_failure_recovery",
        "note": row["note"],
    }
    return analysis, {"rows": [row]}
