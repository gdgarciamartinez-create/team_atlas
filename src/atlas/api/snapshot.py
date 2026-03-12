from __future__ import annotations

from typing import Any, Dict, Optional
from fastapi import APIRouter, Query

from atlas.data.market_data import get_candles_payload
from atlas.runtime import runtime

from atlas.bot.gatillo.engine import eval_gatillo
from atlas.bot.gap.engine import eval_gap
from atlas.bot.presesion.engine import eval_presesion
from atlas.bot.atlas_ia.engine import eval_atlas_ia

router = APIRouter()

# Cache simple en memoria para conservar las últimas velas válidas
SNAPSHOT_CANDLES_CACHE: dict[str, list] = {}


def _normalize_world(w: Optional[str]) -> str:
    return (w or "").strip().upper()


def _fixed_tf(world: str, atlas_mode: Optional[str], tf: str) -> str:
    w = (world or "").upper().strip()
    mode = (atlas_mode or "").upper().strip()

    if w == "GAP":
        return "M1"

    if w == "PRESESION":
        return "M5"

    if w == "ATLAS_IA":
        if mode == "SCALPING_M1":
            return "M1"
        if mode == "SCALPING_M5":
            return "M5"
        if mode == "FOREX":
            return "H1"

    return tf


def _cache_key(
    world: str,
    atlas_mode: Optional[str],
    symbol: str,
    tf: str,
    count: int,
) -> str:
    return f"{world}|{(atlas_mode or '').upper()}|{symbol}|{tf}|{int(count)}"


def _extract_valid_candles(md: Dict[str, Any]) -> list:
    candles = md.get("candles", [])
    if isinstance(candles, list) and len(candles) >= 2:
        return candles
    return []


@router.get("/snapshot")
def snapshot(
    world: str = Query("ATLAS_IA"),
    symbol: str = Query("EURUSDz"),
    tf: str = Query("M5"),
    count: int = Query(220),
    atlas_mode: Optional[str] = Query(None),
    bias: Optional[str] = Query(None),
    floor: Optional[float] = Query(None),
    ceiling: Optional[float] = Query(None),
    debug: bool = Query(False),
    lite: bool = Query(True),
) -> Dict[str, Any]:
    w = _normalize_world(world)
    fixed_tf = _fixed_tf(w, atlas_mode, tf)
    cache_key = _cache_key(
        world=w,
        atlas_mode=atlas_mode,
        symbol=symbol,
        tf=fixed_tf,
        count=int(count),
    )

    md = get_candles_payload(symbol=symbol, tf=fixed_tf, count=int(count))

    fresh_candles = _extract_valid_candles(md)
    cached_candles = SNAPSHOT_CANDLES_CACHE.get(cache_key, [])

    # Si llegaron velas buenas, actualizamos cache
    if fresh_candles:
        SNAPSHOT_CANDLES_CACHE[cache_key] = fresh_candles

    # Velas finales: priorizar frescas, si no usar cache
    final_candles = fresh_candles if fresh_candles else cached_candles

    # md_for_eval: si md vino mal pero hay cache, usamos cache para que el motor no quede ciego
    md_for_eval = dict(md)
    md_for_eval["candles"] = final_candles
    md_for_eval["ok"] = bool(final_candles)
    if not md_for_eval["ok"] and not md_for_eval.get("reason"):
        md_for_eval["reason"] = "no candles"

    base: Dict[str, Any] = {
        "ok": bool(final_candles),
        "world": w,
        "symbol": symbol,
        "tf": fixed_tf,
        "count": int(count),
        "atlas_mode": atlas_mode,
        "candles": final_candles,
        "last_error": md.get("last_error"),
        "feed": md.get("feed"),
        "control": runtime.get_control_state(),
    }

    if not final_candles:
        base["analysis"] = {
            "world": w,
            "status": "NO_DATA",
            "reason": md.get("reason") or md.get("error") or "no candles",
        }
        base["ui"] = {"rows": []}
        return base

    raw_query = {
        "world": w,
        "symbol": symbol,
        "tf": fixed_tf,
        "count": int(count),
        "atlas_mode": atlas_mode,
        "bias": bias,
        "floor": floor,
        "ceiling": ceiling,
        "debug": debug,
        "lite": lite,
    }

    try:
        if w == "GATILLO":
            analysis, ui = eval_gatillo(md_for_eval, raw_query=raw_query)
        elif w == "GAP":
            analysis, ui = eval_gap(md_for_eval, raw_query=raw_query)
        elif w == "PRESESION":
            analysis, ui = eval_presesion(md_for_eval, raw_query=raw_query)
        elif w == "ATLAS_IA":
            analysis, ui = eval_atlas_ia(md_for_eval, raw_query=raw_query)
        else:
            analysis = {
                "world": w,
                "status": "UNKNOWN_WORLD",
                "reason": f"Unknown world: {w}",
                "raw_query": raw_query,
            }
            ui = {"rows": []}

        rows = []
        if isinstance(ui, dict):
            raw_rows = ui.get("rows", [])
            if isinstance(raw_rows, list):
                rows = [
                    runtime.merge_row_with_freeze(row)
                    for row in raw_rows
                    if isinstance(row, dict)
                ]

        base["analysis"] = analysis
        base["ui"] = {
            **(ui if isinstance(ui, dict) else {}),
            "rows": rows,
        }
        base["ok"] = base["ok"] and (analysis.get("status") not in ("IMPORT_ERROR", "CRASH"))
        return base

    except Exception as e:
        base["analysis"] = {
            "world": w,
            "status": "CRASH",
            "reason": f"snapshot crash: {repr(e)}",
            "raw_query": raw_query,
        }
        base["ui"] = {"rows": []}
        base["ok"] = False
        return base