from __future__ import annotations

from typing import Any, Callable, Dict, Optional


def _lazy_call(module_path: str, fn_name: str, **kwargs) -> Dict[str, Any]:
    mod = __import__(module_path, fromlist=[fn_name])
    fn: Callable[..., Dict[str, Any]] = getattr(mod, fn_name)
    return fn(**kwargs)


def get_snapshot_world(
    world: str,
    symbol: str,
    tf: str,
    count: int,
    atlas_mode: Optional[str] = None,
) -> Dict[str, Any]:
    w = (world or "").upper().strip()

    if w == "FOREX":
        return _lazy_call("atlas.bot.worlds.forex_world", "build_forex_world", symbol=symbol, tf=tf, count=count)

    if w == "SCALPING_M1":
        return _lazy_call("atlas.bot.worlds.scalping_world", "build_scalping_world", symbol=symbol, tf="M1", count=count)

    if w == "SCALPING_M5":
        return _lazy_call("atlas.bot.worlds.scalping_world", "build_scalping_world", symbol=symbol, tf="M5", count=count)

    if w == "GAP":
        return _lazy_call("atlas.bot.worlds.gap_world", "build_gap_world", symbol=symbol, tf=tf, count=count)

    if w == "GATILLO":
        return _lazy_call("atlas.bot.worlds.gatillo_world", "build_gatillo_world", symbol=symbol, tf=tf, count=count)

    if w == "PRESESION":
        return _lazy_call("atlas.bot.worlds.presesion_world", "build_presesion_world", symbol=symbol, tf=tf, count=count)

    if w == "BITACORA":
        from atlas.bot.worlds.feed import get_feed_with_meta
        from atlas.bot.bitacora_store import build_bitacora_world

        candles, meta = get_feed_with_meta(symbol=symbol, tf=tf, n=count)
        return build_bitacora_world(symbol=symbol, tf=tf, candles=candles, meta=meta)

    if w == "ATLAS_IA":
        return _lazy_call(
            "atlas.bot.worlds.atlas_ai_world",
            "build_atlas_ai_world",
            symbol=symbol,
            tf=tf,
            count=count,
            atlas_mode=atlas_mode,
        )

    return {
        "ok": True,
        "world": w,
        "symbol": symbol,
        "tf": tf,
        "ts_ms": 0,
        "candles": [],
        "meta": {},
        "state": "WAIT",
        "side": "WAIT",
        "price": 0.0,
        "zone": (0.0, 0.0),
        "note": f"world no implementado: {w}",
        "score": 0,
        "light": "GRAY",
        "last_error": None,
    }