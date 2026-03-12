from __future__ import annotations

from typing import Any, Dict, List, Optional

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

    candles_by_symbol: Dict[str, Dict[str, Any]] = {}
    feed_errors: List[Dict[str, Any]] = []

    safe_count = int(count)

    for symbol in symbols:
        md = get_candles_payload(symbol=symbol, tf=tf, count=safe_count)

        if not md.get("ok"):
            feed_errors.append(
                {
                    "symbol": symbol,
                    "reason": md.get("reason") or md.get("error") or "no candles",
                    "last_error": md.get("last_error"),
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

    raw_rows = result.get("rows", [])
    if not isinstance(raw_rows, list):
        raw_rows = []

    frozen_rows: List[Dict[str, Any]] = []
    for row in raw_rows:
        if not isinstance(row, dict):
            continue

        merged = runtime.merge_row_with_freeze(row)
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