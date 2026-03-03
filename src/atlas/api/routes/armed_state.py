from __future__ import annotations

import time
from typing import Dict

from fastapi import APIRouter, Query

from atlas.bot.symbol_universe import get_universe_config

router = APIRouter(prefix="/armed", tags=["armed"])

cfg = get_universe_config()

# Estado en memoria (simple) por símbolo MT5
_ARMED_BY_SYMBOL: Dict[str, dict] = {s: {"armed": False, "updated_at": None, "note": ""} for s in cfg.default_mt5_symbols}


def _now() -> float:
    return float(time.time())


def _norm_symbol(symbol: str) -> str:
    s = (symbol or "").strip()
    return s if s else cfg.default_mt5_symbols[0]


@router.get("")
def armed_list():
    return {
        "symbols": list(_ARMED_BY_SYMBOL.keys()),
        "items": _ARMED_BY_SYMBOL,
    }


@router.get("/status")
def armed_status(symbol: str = Query(None, description="MT5 symbol (e.g. XAUUSDz)")):
    s = _norm_symbol(symbol)
    if s not in _ARMED_BY_SYMBOL:
        _ARMED_BY_SYMBOL[s] = {"armed": False, "updated_at": None, "note": ""}
    return {"symbol": s, **_ARMED_BY_SYMBOL[s]}


@router.post("/toggle")
def armed_toggle(symbol: str = Query(None, description="MT5 symbol (e.g. XAUUSDz)")):
    s = _norm_symbol(symbol)
    if s not in _ARMED_BY_SYMBOL:
        _ARMED_BY_SYMBOL[s] = {"armed": False, "updated_at": None, "note": ""}

    cur = bool(_ARMED_BY_SYMBOL[s].get("armed"))
    _ARMED_BY_SYMBOL[s]["armed"] = (not cur)
    _ARMED_BY_SYMBOL[s]["updated_at"] = _now()
    return {"symbol": s, **_ARMED_BY_SYMBOL[s]}


@router.post("/set")
def armed_set(
    value: int = Query(..., description="0/1"),
    symbol: str = Query(None, description="MT5 symbol (e.g. XAUUSDz)"),
    note: str = Query("", description="Optional note"),
):
    s = _norm_symbol(symbol)
    if s not in _ARMED_BY_SYMBOL:
        _ARMED_BY_SYMBOL[s] = {"armed": False, "updated_at": None, "note": ""}

    _ARMED_BY_SYMBOL[s]["armed"] = bool(int(value))
    _ARMED_BY_SYMBOL[s]["updated_at"] = _now()
    _ARMED_BY_SYMBOL[s]["note"] = str(note or "")
    return {"symbol": s, **_ARMED_BY_SYMBOL[s]}