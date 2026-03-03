# src/atlas/bot/worlds/feed.py
from __future__ import annotations

from typing import Any, Dict, List, Tuple
import random
import time

# ============================================================
# Estado global del feed
# ============================================================

_FEED_RUNNING = True
_FEED_STATE: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}


# ============================================================
# Control externo
# ============================================================

def feed_play() -> None:
    global _FEED_RUNNING
    _FEED_RUNNING = True


def feed_pause() -> None:
    global _FEED_RUNNING
    _FEED_RUNNING = False


def feed_reset() -> None:
    global _FEED_STATE
    _FEED_STATE = {}


# ============================================================
# Feed principal
# ============================================================

def get_feed_with_meta(symbol: str, tf: str, n: int = 200):
    key = (symbol, tf)

    candles = _FEED_STATE.get(key)

    if candles is None:
        candles = _seed_candles(n)
        _FEED_STATE[key] = candles

    if _FEED_RUNNING:
        _append_new_candle(candles)

    return candles[-n:], {"running": _FEED_RUNNING}


# ============================================================
# Helpers
# ============================================================

def _seed_candles(n: int) -> List[Dict[str, Any]]:
    base = 5000.0
    candles = []
    for _ in range(n):
        o = base + random.uniform(-10, 10)
        c = o + random.uniform(-5, 5)
        h = max(o, c) + random.uniform(0, 3)
        l = min(o, c) - random.uniform(0, 3)
        candles.append(_mk_candle(o, h, l, c))
        base = c
    return candles


def _append_new_candle(candles: List[Dict[str, Any]]) -> None:
    last = candles[-1]
    base = float(last["c"])

    o = base
    c = o + random.uniform(-6, 6)
    h = max(o, c) + random.uniform(0, 2)
    l = min(o, c) - random.uniform(0, 2)

    candles.append(_mk_candle(o, h, l, c))


def _mk_candle(o: float, h: float, l: float, c: float) -> Dict[str, Any]:
    return {
        "t": int(time.time() * 1000),
        "o": float(o),
        "h": float(h),
        "l": float(l),
        "c": float(c),
    }