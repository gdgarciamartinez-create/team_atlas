from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Tuple
from zoneinfo import ZoneInfo

from atlas.core.presesion_calc import calc_presesion_from_candles


TZ_SCL = ZoneInfo("America/Santiago")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


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
    setup_type: str = "presesion_range_reclaim",
) -> Dict[str, Any]:
    return {
        "symbol": symbol,
        "tf": tf,
        "world": "PRESESION",
        "atlas_mode": "PRESESION",
        "side": side,
        "state": state,
        "entry": float(entry),
        "sl": float(sl),
        "tp": float(tp),
        "score": int(score),
        "setup_type": setup_type,
        "note": note,
    }


def eval_presesion(md: Dict[str, Any], raw_query: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    candles = md.get("candles") or []
    symbol = str(raw_query.get("symbol") or "")
    tf = str(raw_query.get("tf") or "M5").upper().strip()
    ts_ms = int(datetime.now(TZ_SCL).timestamp() * 1000)
    info = calc_presesion_from_candles(candles, symbol=symbol, tf=tf, ts_ms=ts_ms)

    wait_row = _row(
        symbol=symbol,
        tf=tf,
        side="WAIT",
        state="WAIT",
        entry=0.0,
        sl=0.0,
        tp=0.0,
        score=0,
        note="PRESESION waiting",
        setup_type="presesion_range_reclaim",
    )

    if not bool(info.get("in_window")):
        analysis = {
            "world": "PRESESION",
            "status": "SLEEP",
            "state": "WAIT",
            "reason": "OUT_OF_WINDOW",
            "note": "PRESESION fuera de ventana",
        }
        wait_row["note"] = "PRESESION fuera de ventana"
        return analysis, {"rows": [wait_row]}

    if len(candles) < 8:
        analysis = {
            "world": "PRESESION",
            "status": "OK",
            "state": "WAIT",
            "reason": "NO_DATA",
            "note": "PRESESION sin velas suficientes",
        }
        wait_row["note"] = "PRESESION sin velas suficientes"
        return analysis, {"rows": [wait_row]}

    range_source = candles[-7:-1] if len(candles) >= 7 else candles[:-1]
    if not range_source:
        analysis = {
            "world": "PRESESION",
            "status": "OK",
            "state": "WAIT",
            "reason": "NO_RANGE",
            "note": "PRESESION sin rango valido",
        }
        wait_row["note"] = "PRESESION sin rango valido"
        return analysis, {"rows": [wait_row]}

    range_high = max(_safe_float(c.get("h", c.get("high")), 0.0) for c in range_source)
    range_low = min(_safe_float(c.get("l", c.get("low")), 0.0) for c in range_source)

    last = candles[-1]
    last_high = _safe_float(last.get("h", last.get("high")), 0.0)
    last_low = _safe_float(last.get("l", last.get("low")), 0.0)
    last_close = _safe_float(last.get("c", last.get("close")), 0.0)

    sweep_up = last_high > range_high
    sweep_down = last_low < range_low
    recovery_sell = sweep_up and last_close < range_high
    recovery_buy = sweep_down and last_close > range_low

    if not sweep_up and not sweep_down:
        analysis = {
            "world": "PRESESION",
            "status": "OK",
            "state": "WAIT",
            "reason": "WAIT_SWEEP",
            "note": "PRESESION esperando barrida del rango",
        }
        wait_row["note"] = "PRESESION esperando barrida del rango"
        return analysis, {"rows": [wait_row]}

    if sweep_up and not recovery_sell:
        row = _row(
            symbol=symbol,
            tf=tf,
            side="SELL",
            state="SET_UP",
            entry=last_close,
            sl=range_high,
            tp=range_low,
            score=8,
            setup_type="presesion_range_reclaim",
            note="PRESESION set-up: sweep del rango, faltando recuperacion",
        )
        analysis = {
            "world": "PRESESION",
            "status": "OK",
            "state": "SET_UP",
            "reason": "SWEEP_NO_RECOVERY",
            "setup_type": "presesion_range_reclaim",
            "note": row["note"],
        }
        return analysis, {"rows": [row]}

    if sweep_down and not recovery_buy:
        row = _row(
            symbol=symbol,
            tf=tf,
            side="BUY",
            state="SET_UP",
            entry=last_close,
            sl=range_low,
            tp=range_high,
            score=8,
            setup_type="presesion_range_reclaim",
            note="PRESESION set-up: sweep del rango, faltando recuperacion",
        )
        analysis = {
            "world": "PRESESION",
            "status": "OK",
            "state": "SET_UP",
            "reason": "SWEEP_NO_RECOVERY",
            "setup_type": "presesion_range_reclaim",
            "note": row["note"],
        }
        return analysis, {"rows": [row]}

    if recovery_sell:
        row = _row(
            symbol=symbol,
            tf=tf,
            side="SELL",
            state="ENTRY",
            entry=last_close,
            sl=range_high,
            tp=range_low,
            score=9,
            setup_type="presesion_range_sweep_recovery",
            note="PRESESION entry: rango -> barrida -> recuperacion",
        )
        analysis = {
            "world": "PRESESION",
            "status": "OK",
            "state": "ENTRY",
            "reason": "RECOVERY_CONFIRMED",
            "setup_type": "presesion_range_sweep_recovery",
            "note": row["note"],
        }
        return analysis, {"rows": [row]}

    row = _row(
        symbol=symbol,
        tf=tf,
        side="BUY",
        state="ENTRY",
        entry=last_close,
        sl=range_low,
        tp=range_high,
        score=9,
        setup_type="presesion_range_sweep_recovery",
        note="PRESESION entry: rango -> barrida -> recuperacion",
    )
    analysis = {
        "world": "PRESESION",
        "status": "OK",
        "state": "ENTRY",
        "reason": "RECOVERY_CONFIRMED",
        "setup_type": "presesion_range_sweep_recovery",
        "note": row["note"],
    }
    return analysis, {"rows": [row]}
