from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Query

from atlas.data.market_data import get_candles_payload
from atlas.runtime import runtime

router = APIRouter(tags=["snapshot"])

# Cache simple de velas para evitar gráficos vacíos
_CANDLE_CACHE: Dict[str, list] = {}


def _cache_key(symbol: str, tf: str, count: int) -> str:
    return f"{symbol}|{tf}|{count}"


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


@router.get("/snapshot")
def snapshot(
    world: str = Query("ATLAS_IA"),
    atlas_mode: str = Query("SCALPING_M1"),
    symbol: Optional[str] = Query(None),
    count: int = Query(200, ge=50, le=500),
) -> Dict[str, Any]:

    w = _normalize_world(world)
    mode = _normalize_mode(atlas_mode)

    selected_symbol = symbol or "XAUUSDz"
    tf = _tf_for(w, mode)

    md = get_candles_payload(symbol=selected_symbol, tf=tf, count=int(count))

    cache_key = _cache_key(selected_symbol, tf, int(count))

    fresh_candles = md.get("candles", []) if md.get("ok") else []
    cached_candles = _CANDLE_CACHE.get(cache_key, [])

    # Si llegaron velas buenas, actualizar cache
    if fresh_candles and len(fresh_candles) >= 2:
        _CANDLE_CACHE[cache_key] = fresh_candles
        candles = fresh_candles
    else:
        candles = cached_candles

    # Si ni siquiera hay cache
    if not candles:
        return {
            "ok": False,
            "world": w,
            "symbol": selected_symbol,
            "tf": tf,
            "count": int(count),
            "atlas_mode": mode,
            "analysis": {
                "status": "NO_DATA",
                "world": w,
            },
            "ui": {
                "rows": [],
                "meta": {},
            },
            "reason": md.get("reason") or md.get("error") or "no candles",
            "last_error": md.get("last_error"),
            "control": runtime.get_control_state(),
        }

    active = runtime.get_active_plan(selected_symbol, tf)

    analysis = {
        "status": "OK",
        "world": w,
    }

    if active:
        analysis.update(
            {
                "state": active.get("state"),
                "side": active.get("side"),
                "entry": active.get("entry"),
                "sl": active.get("sl"),
                "tp": active.get("tp"),
                "text": active.get("note"),
            }
        )

    row = {
        "symbol": selected_symbol,
        "tf": tf,
        "score": active.get("score") if active else None,
        "side": active.get("side") if active else None,
        "lot": active.get("lot") if active else None,
        "state": active.get("state") if active else "SIN_SETUP",
        "entry": active.get("entry") if active else None,
        "sl": active.get("sl") if active else None,
        "tp": active.get("tp") if active else None,
        "note": active.get("note") if active else None,
        "updated_at": active.get("updated_at") if active else None,
        "world": w,
        "atlas_mode": mode,
        "price": candles[-1].get("c") if candles else None,
    }

    return {
        "ok": True,
        "world": w,
        "symbol": selected_symbol,
        "tf": tf,
        "count": int(count),
        "atlas_mode": mode,
        "analysis": analysis,
        "ui": {
            "rows": [row],
            "meta": {},
        },
        "candles": candles,
        "control": runtime.get_control_state(),
    }