from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query

from atlas.data.market_data import get_candles_payload
from atlas.runtime import runtime

router = APIRouter(tags=["snapshot"])
TZ_SCL = ZoneInfo("America/Santiago")

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
    window_state = _window_state(w)

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
                "floating_price_move": None,
                "floating_point_move": None,
                "floating_pip_move": None,
                "floating_usd": None,
                "trade_pnl_state": "FLAT",
            },
            "ui": {
                "rows": [],
                "meta": {},
            },
            "reason": md.get("reason") or md.get("error") or "no candles",
            "last_error": md.get("last_error"),
            "control": runtime.get_control_state(),
        }

    if window_state["sleep"]:
        analysis = {
            "status": "SLEEP",
            "world": w,
            "note": window_state["note"],
            "window": window_state["window"],
            "season_mode": window_state["season_mode"],
            "now_santiago": window_state["now_santiago"],
            "floating_price_move": None,
            "floating_point_move": None,
            "floating_pip_move": None,
            "floating_usd": None,
            "trade_pnl_state": "FLAT",
        }

        row = {
            "symbol": selected_symbol,
            "tf": tf,
            "score": None,
            "side": None,
            "lot": None,
            "lot_raw": None,
            "lot_capped": None,
            "lot_cap_reason": None,
            "state": "SIN_SETUP",
            "text": "SIN_SETUP",
            "entry": None,
            "sl": None,
            "tp": None,
            "tp1": None,
            "tp1_price": None,
            "tp2": None,
            "parcial": None,
            "zone_low": None,
            "zone_high": None,
            "note": window_state["note"],
            "updated_at": None,
            "world": w,
            "atlas_mode": mode,
            "price": candles[-1].get("c") if candles else None,
            "floating_price_move": None,
            "floating_point_move": None,
            "floating_pip_move": None,
            "floating_usd": None,
            "trade_pnl_state": "FLAT",
        }
    else:
        active = runtime.get_active_plan(
            selected_symbol,
            tf,
            world=w,
            atlas_mode=mode,
            live_price=candles[-1].get("c") if candles else None,
        )

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
                    "tp1": active.get("tp1"),
                    "tp2": active.get("tp2"),
                    "text": active.get("text"),
                    "note": active.get("note"),
                    "floating_price_move": active.get("floating_price_move"),
                    "floating_point_move": active.get("floating_point_move"),
                    "floating_pip_move": active.get("floating_pip_move"),
                    "floating_usd": active.get("floating_usd"),
                    "trade_pnl_state": active.get("trade_pnl_state"),
                    "active_trade_id": active.get("trade_id"),
                    "active_parent_trade_id": active.get("parent_trade_id"),
                    "current_leg_id": active.get("leg_id"),
                    "active_partial_status": active.get("is_partial"),
                    "active_lot": active.get("lot"),
                    "active_risk_percent": active.get("risk_percent"),
                }
            )

        row = {
            "symbol": selected_symbol,
            "tf": tf,
            "score": None,
            "side": None,
            "lot": None,
            "lot_raw": None,
            "lot_capped": None,
            "lot_cap_reason": None,
            "state": "SIN_SETUP",
            "text": "SIN_SETUP",
            "entry": None,
            "sl": None,
            "tp": None,
            "tp1": None,
            "tp1_price": None,
            "tp2": None,
            "parcial": None,
            "zone_low": None,
            "zone_high": None,
            "note": None,
            "updated_at": None,
            "world": w,
            "atlas_mode": mode,
            "price": candles[-1].get("c") if candles else None,
            "floating_price_move": None,
            "floating_point_move": None,
            "floating_pip_move": None,
            "floating_usd": None,
            "trade_pnl_state": "FLAT",
            "trade_id": None,
            "parent_trade_id": None,
            "leg_id": None,
            "is_partial": None,
            "partial_percent": None,
            "risk_percent": None,
        }

        if active:
            row.update(
                {
                    "score": active.get("score"),
                    "side": active.get("side"),
                    "lot": active.get("lot"),
                    "lot_raw": active.get("lot_raw"),
                    "lot_capped": active.get("lot_capped"),
                    "lot_cap_reason": active.get("lot_cap_reason"),
                    "state": active.get("state"),
                    "text": active.get("text"),
                    "entry": active.get("entry"),
                    "sl": active.get("sl"),
                    "tp": active.get("tp"),
                    "tp1": active.get("tp1"),
                    "tp1_price": active.get("tp1_price"),
                    "tp2": active.get("tp2"),
                    "parcial": active.get("parcial"),
                    "zone_low": active.get("zone_low"),
                    "zone_high": active.get("zone_high"),
                    "note": active.get("note"),
                    "updated_at": active.get("updated_at"),
                    "floating_price_move": active.get("floating_price_move"),
                    "floating_point_move": active.get("floating_point_move"),
                    "floating_pip_move": active.get("floating_pip_move"),
                    "floating_usd": active.get("floating_usd"),
                    "trade_pnl_state": active.get("trade_pnl_state"),
                    "trade_id": active.get("trade_id"),
                    "parent_trade_id": active.get("parent_trade_id"),
                    "leg_id": active.get("leg_id"),
                    "is_partial": active.get("is_partial"),
                    "partial_percent": active.get("partial_percent"),
                    "risk_percent": active.get("risk_percent"),
                }
            )

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
