# src/atlas/bot/stats/fib_stats.py
from __future__ import annotations

import math
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple


# -----------------------------------------------------------------------------
# Utilidades
# -----------------------------------------------------------------------------

def _now_ms() -> int:
    return int(time.time() * 1000)


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _candle_ohlc(c: Dict[str, Any]) -> Tuple[float, float, float, float]:
    return (
        _safe_float(c.get("o"), 0.0),
        _safe_float(c.get("h"), 0.0),
        _safe_float(c.get("l"), 0.0),
        _safe_float(c.get("c"), 0.0),
    )


def _last_close(candles: List[Dict[str, Any]]) -> float:
    if not candles:
        return 0.0
    return _safe_float(candles[-1].get("c"), 0.0)


# -----------------------------------------------------------------------------
# Estadística adaptativa (online)
# -----------------------------------------------------------------------------

@dataclass
class FibLiveStats:
    symbol: str
    tf: str

    # conteos
    n_obs: int = 0

    # probabilidades online (EWMA)
    p_reach_618: float = 0.0
    p_reach_786: float = 0.0
    p_reach_100: float = 0.0
    p_overshoot_100: float = 0.0

    # profundidad típica (EWMA)
    depth_med: float = 0.0

    # control
    last_ts_ms: int = 0
    updated_ts_ms: int = 0


# store in-memory
_STORE: Dict[str, FibLiveStats] = {}


def _key(symbol: str, tf: str) -> str:
    return f"{symbol}::{tf}"


def _ewma(prev: float, x: float, alpha: float) -> float:
    if prev == 0.0:
        return x
    return (alpha * x) + ((1.0 - alpha) * prev)


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _pivot_points(closes: List[float], k: int = 2) -> List[Tuple[int, str]]:
    """
    Pivotes simples sobre cierres.
    Devuelve lista de (idx, "H"/"L") con pivot high/low.

    k=2 => un pivot es mayor/menor que 2 velas a cada lado.
    """
    n = len(closes)
    if n < (2 * k + 3):
        return []
    piv: List[Tuple[int, str]] = []
    for i in range(k, n - k):
        c = closes[i]
        left = closes[i - k:i]
        right = closes[i + 1:i + 1 + k]
        if all(c > x for x in left) and all(c > x for x in right):
            piv.append((i, "H"))
        if all(c < x for x in left) and all(c < x for x in right):
            piv.append((i, "L"))
    return piv


def _last_swing_depth_ratio(candles: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Saca el último swing “usable”:
    - detecta pivotes en cierres
    - toma los 2 pivotes más recientes de tipo alternado (L->H o H->L)
    - estima “pullback” posterior y calcula ratio de retroceso

    Retorna:
    {
      "dir": "UP"/"DOWN",
      "hi": float, "lo": float,
      "depth": float (0.. >1),
      "reach_618": bool,
      "reach_786": bool,
      "reach_100": bool,
      "overshoot_100": bool
    }
    """
    if len(candles) < 30:
        return None

    closes = [_safe_float(c.get("c"), 0.0) for c in candles]
    piv = _pivot_points(closes, k=2)
    if len(piv) < 2:
        return None

    # tomar los últimos 2 pivotes alternados
    piv_sorted = piv[-8:]  # ventana pequeña para buscar alternancia reciente
    last = piv_sorted[-1]
    prev = None
    for j in range(len(piv_sorted) - 2, -1, -1):
        if piv_sorted[j][1] != last[1]:
            prev = piv_sorted[j]
            break
    if prev is None:
        return None

    i1, t1 = prev
    i2, t2 = last

    # Si prev es L y last es H => impulso UP
    # Si prev es H y last es L => impulso DOWN
    c1 = closes[i1]
    c2 = closes[i2]
    if c1 == 0.0 or c2 == 0.0 or i2 <= i1:
        return None

    # tramo posterior para medir pullback (desde i2 hasta el final)
    post = closes[i2:]
    if len(post) < 6:
        return None

    if t1 == "L" and t2 == "H":
        lo = c1
        hi = c2
        rng = hi - lo
        if rng <= 0:
            return None
        # pullback = mínimo posterior desde hi
        pb = min(post)
        depth = (hi - pb) / rng  # 0.0.. >1.0
        return {
            "dir": "UP",
            "hi": hi,
            "lo": lo,
            "depth": depth,
            "reach_618": depth >= 0.618,
            "reach_786": depth >= 0.786,
            "reach_100": depth >= 1.0,
            "overshoot_100": depth > 1.0,
        }

    if t1 == "H" and t2 == "L":
        hi = c1
        lo = c2
        rng = hi - lo
        if rng <= 0:
            return None
        # pullback = máximo posterior desde lo
        pb = max(post)
        depth = (pb - lo) / rng
        return {
            "dir": "DOWN",
            "hi": hi,
            "lo": lo,
            "depth": depth,
            "reach_618": depth >= 0.618,
            "reach_786": depth >= 0.786,
            "reach_100": depth >= 1.0,
            "overshoot_100": depth > 1.0,
        }

    return None


def update_fib_stats(symbol: str, tf: str, candles: List[Dict[str, Any]], alpha: float = 0.18) -> FibLiveStats:
    """
    Actualiza estadísticas live desde la ventana de velas (online).
    alpha: EWMA smoothing. 0.18 = relativamente reactivo, sin volverse loco.
    """
    k = _key(symbol, tf)
    s = _STORE.get(k)
    if s is None:
        s = FibLiveStats(symbol=symbol, tf=tf)
        _STORE[k] = s

    # Evitar “recalcular sin nuevas velas”
    last_ts = 0
    try:
        last_ts = int(candles[-1].get("t", 0)) if candles else 0
    except Exception:
        last_ts = 0

    if last_ts != 0 and last_ts == s.last_ts_ms:
        return s

    obs = _last_swing_depth_ratio(candles)
    if obs is None:
        # igual marcamos timestamp para no spamear
        s.last_ts_ms = last_ts or s.last_ts_ms
        s.updated_ts_ms = _now_ms()
        return s

    depth = float(obs["depth"])
    r618 = 1.0 if obs["reach_618"] else 0.0
    r786 = 1.0 if obs["reach_786"] else 0.0
    r100 = 1.0 if obs["reach_100"] else 0.0
    ov = 1.0 if obs["overshoot_100"] else 0.0

    s.n_obs += 1
    s.depth_med = _ewma(s.depth_med, depth, alpha)

    s.p_reach_618 = _clamp01(_ewma(s.p_reach_618, r618, alpha))
    s.p_reach_786 = _clamp01(_ewma(s.p_reach_786, r786, alpha))
    s.p_reach_100 = _clamp01(_ewma(s.p_reach_100, r100, alpha))
    s.p_overshoot_100 = _clamp01(_ewma(s.p_overshoot_100, ov, alpha))

    s.last_ts_ms = last_ts or s.last_ts_ms
    s.updated_ts_ms = _now_ms()
    return s


def get_fib_profile(symbol: str, tf: str) -> Dict[str, Any]:
    """
    Perfil “humano” derivado de stats.
    No decide trades. Solo describe sesgo probabilístico.
    """
    s = _STORE.get(_key(symbol, tf))
    if s is None:
        return {
            "ok": True,
            "symbol": symbol,
            "tf": tf,
            "n_obs": 0,
            "note": "sin stats aún",
            "live": {},
            "bias": {},
        }

    live = asdict(s)

    bias: Dict[str, Any] = {}
    # interpretación
    if s.n_obs < 12:
        bias["confidence"] = "LOW"
    elif s.n_obs < 40:
        bias["confidence"] = "MID"
    else:
        bias["confidence"] = "HIGH"

    bias["depth_style"] = "DEEP" if s.depth_med >= 0.78 else "MID" if s.depth_med >= 0.62 else "SHALLOW"
    bias["likes_786"] = s.p_reach_786 >= 0.55
    bias["likes_100_or_more"] = s.p_reach_100 >= 0.45
    bias["stop_hunt_prone"] = s.p_overshoot_100 >= 0.40

    # recomendación de ejecución (solo sugerencia, no orden)
    if bias["stop_hunt_prone"]:
        bias["execution_hint"] = "si llega a 1.0 con fuerza, endurecer confirmación (no toque)"
    elif bias["likes_786"]:
        bias["execution_hint"] = "esperar profundidad y confirmación; suele respetar 0.786"
    else:
        bias["execution_hint"] = "activo de pullback superficial; no perseguir si no llega"

    return {
        "ok": True,
        "symbol": symbol,
        "tf": tf,
        "n_obs": s.n_obs,
        "note": "fib stats live (EWMA)",
        "live": live,
        "bias": bias,
    }