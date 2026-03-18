from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query

from atlas.bot.atlas_ia.scanner import scan_opportunities
from atlas.data.market_data import get_candles_payload
from atlas.runtime import runtime

router = APIRouter(tags=["scan"])


ATLAS_SYMBOLS = [
    "XAUUSDz",
    "EURUSDz",
    "GBPUSDz",
    "USDJPYz",
    "USDCHFz",
    "USDCADz",
    "AUDUSDz",
    "NZDUSDz",
    "EURJPYz",
    "EURGBPz",
    "EURCADz",
    "EURAUDz",
    "GBPNZDz",
    "BTCUSDz",
    "USTECz",
    "USOILz",
]

PRESESION_SYMBOLS = [
    "EURUSDz",
    "GBPUSDz",
    "AUDUSDz",
    "NZDUSDz",
    "USDJPYz",
    "USDCHFz",
    "USDCADz",
    "EURJPYz",
    "EURGBPz",
    "EURCADz",
    "EURAUDz",
]

GAP_SYMBOLS = ["XAUUSDz"]
TZ_SCL = ZoneInfo("America/Santiago")


def _normalize_world(w: Optional[str]) -> str:
    return (w or "ATLAS_IA").strip().upper()


def _normalize_mode(m: Optional[str]) -> str:
    return (m or "SCALPING_M1").strip().upper()


def _tf_for(world: str, atlas_mode: str) -> str:
    if world == "GAP":
        return "M1"
    if world == "PRESESION":
        return "M5"
    if world == "ATLAS_IA":
        if atlas_mode == "SCALPING_M1":
            return "M1"
        if atlas_mode == "SCALPING_M5":
            return "M5"
        if atlas_mode == "FOREX":
            return "H1"
    return "M5"


def _symbols_for(world: str) -> List[str]:
    if world == "PRESESION":
        return PRESESION_SYMBOLS
    if world == "GAP":
        return GAP_SYMBOLS
    return ATLAS_SYMBOLS


def _in_minutes_window(
    hh: int,
    mm: int,
    start_h: int,
    start_m: int,
    end_h: int,
    end_m: int,
) -> bool:
    now_m = hh * 60 + mm
    start = start_h * 60 + start_m
    end = end_h * 60 + end_m
    return start <= now_m <= end


def _window_state(world: str) -> Dict[str, Any]:
    now = datetime.now(TZ_SCL)
    is_summer = bool(now.dst())
    hh = now.hour
    mm = now.minute

    if world == "GAP":
        if is_summer:
            in_window = _in_minutes_window(hh, mm, 20, 55, 21, 30)
            window = "20:55-21:30"
            season = "SUMMER"
        else:
            in_window = _in_minutes_window(hh, mm, 19, 55, 20, 30)
            window = "19:55-20:30"
            season = "WINTER"
        return {
            "sleep": not in_window,
            "status": "OK" if in_window else "SLEEP",
            "note": "GAP activo" if in_window else "GAP fuera de ventana",
            "window": window,
            "season_mode": season,
            "now_santiago": now.isoformat(),
        }

    if world == "PRESESION":
        in_window = _in_minutes_window(hh, mm, 7, 0, 11, 0)
        return {
            "sleep": not in_window,
            "status": "OK" if in_window else "SLEEP",
            "note": "PRESESION activa" if in_window else "PRESESION fuera de ventana",
            "window": "07:00-11:00",
            "season_mode": "SUMMER" if is_summer else "WINTER",
            "now_santiago": now.isoformat(),
        }

    return {
        "sleep": False,
        "status": "OK",
        "note": "",
        "window": None,
        "season_mode": "SUMMER" if is_summer else "WINTER",
        "now_santiago": now.isoformat(),
    }


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _build_summary(rows: List[Dict[str, Any]], mode: str, symbols: List[str]) -> Dict[str, Any]:
    total_rows = len(rows)

    setups = 0
    entries = 0
    live = 0

    top_entry = None
    top_setup = None
    top_live = None

    best_entry_score = -1.0
    best_setup_score = -1.0
    best_live_score = -1.0

    for row in rows:
        state = str(row.get("state") or "").upper().strip()
        score = _safe_float(row.get("score"), 0.0)

        if state == "SET_UP":
            setups += 1
            if score > best_setup_score:
                best_setup_score = score
                top_setup = row.get("symbol")

        if state == "ENTRY":
            entries += 1
            if score > best_entry_score:
                best_entry_score = score
                top_entry = row.get("symbol")

        if state in {"IN_TRADE", "TP1", "TP2", "RUN"}:
            live += 1
            if score > best_live_score:
                best_live_score = score
                top_live = row.get("symbol")

    return {
        "mode": mode,
        "total_symbols": len(symbols),
        "total_rows": total_rows,
        "entries": entries,
        "setups": setups,
        "live": live,
        "top_entry": top_entry,
        "top_setup": top_setup,
        "top_live": top_live,
    }


@router.get("/scan")
def scan(
    world: str = Query("ATLAS_IA"),
    atlas_mode: str = Query("SCALPING_M1"),
    count: int = Query(80, ge=20, le=500),
) -> Dict[str, Any]:
    w = _normalize_world(world)
    mode = _normalize_mode(atlas_mode)
    tf = _tf_for(w, mode)
    symbols = _symbols_for(w)
    window_state = _window_state(w)

    if window_state["sleep"]:
        return {
            "ok": True,
            "world": w,
            "atlas_mode": mode,
            "tf": tf,
            "count": int(count),
            "symbols": symbols,
            "summary": {
                "mode": mode,
                "total_symbols": len(symbols),
                "total_rows": 0,
                "entries": 0,
                "setups": 0,
                "live": 0,
                "top_entry": None,
                "top_setup": None,
                "top_live": None,
            },
            "rows": [],
            "analysis": {
                "status": "SLEEP",
                "note": window_state["note"],
                "window": window_state["window"],
                "season_mode": window_state["season_mode"],
                "now_santiago": window_state["now_santiago"],
            },
            "feed_errors": [],
            "control": runtime.get_control_state(),
        }

    candles_by_symbol: Dict[str, Dict[str, Any]] = {}
    feed_errors: List[Dict[str, Any]] = []

    safe_count = int(count)

    for symbol in symbols:
        md = get_candles_payload(symbol=symbol, tf=tf, count=safe_count)

        if not isinstance(md, dict) or not md.get("ok"):
            feed_errors.append(
                {
                    "symbol": symbol,
                    "reason": (md or {}).get("reason") or (md or {}).get("error") or "no candles",
                    "last_error": (md or {}).get("last_error"),
                }
            )
            candles_by_symbol[symbol] = {"candles": []}
            continue

        candles = md.get("candles", [])
        if not isinstance(candles, list):
            candles = []

        candles_by_symbol[symbol] = {
            "candles": candles,
        }

    result = scan_opportunities(
        atlas_mode=mode,
        candles_by_symbol=candles_by_symbol,
    )

    if not isinstance(result, dict):
        result = {"rows": []}

    raw_rows = result.get("rows", [])
    if not isinstance(raw_rows, list):
        raw_rows = []

    frozen_rows: List[Dict[str, Any]] = []
    for row in raw_rows:
        if not isinstance(row, dict):
            continue

        row_with_context = dict(row)
        row_with_context["world"] = row_with_context.get("world") or w
        row_with_context["atlas_mode"] = row_with_context.get("atlas_mode") or mode

        merged = runtime.merge_row_with_freeze(row_with_context)
        if isinstance(merged, dict):
            frozen_rows.append(merged)

    summary = _build_summary(frozen_rows, mode, symbols)

    return {
        "ok": True,
        "world": w,
        "atlas_mode": mode,
        "tf": tf,
        "count": safe_count,
        "symbols": symbols,
        "summary": summary,
        "rows": frozen_rows,
        "feed_errors": feed_errors,
        "control": runtime.get_control_state(),
    }
