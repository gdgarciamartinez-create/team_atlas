from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple


# =============================================================================
# CONFIG
# =============================================================================

DEFAULT_ZIGZAG_PCT = 0.0012      # 0.12% para pivotes (ajustable)
DEFAULT_LOOKAHEAD = 40           # velas para buscar el retroceso post-impulso
MIN_SWINGS_FOR_CONF = 12         # si hay menos, se marca como "low_conf"

# Persistencia (simple y segura). Si no querés archivo, ponelo None.
PERSIST_PATH = os.path.join("data", "fibo_stats.json")


def _now_ms() -> int:
    return int(time.time() * 1000)


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _closes(candles: List[Dict[str, Any]]) -> List[float]:
    return [_safe_float(c.get("c"), 0.0) for c in candles if isinstance(c, dict)]


def _median(xs: List[float]) -> float:
    ys = [x for x in xs if x is not None]
    ys.sort()
    if not ys:
        return 0.0
    mid = len(ys) // 2
    if len(ys) % 2 == 1:
        return ys[mid]
    return (ys[mid - 1] + ys[mid]) / 2.0


# =============================================================================
# ZigZag pivots (simple y robusto)
# =============================================================================

@dataclass
class Pivot:
    idx: int
    price: float
    kind: str  # "H" o "L"


def _zigzag_pivots(prices: List[float], pct: float) -> List[Pivot]:
    """
    Zigzag minimalista:
    - Detecta cambios de dirección cuando el precio se mueve >= pct desde el extremo actual.
    """
    if len(prices) < 10:
        return []

    pivots: List[Pivot] = []

    # inicio: tomamos el primer precio como base
    last_p = prices[0]
    hi = last_p
    lo = last_p
    hi_i = 0
    lo_i = 0

    direction = 0  # 0 unknown, 1 up, -1 down

    for i in range(1, len(prices)):
        p = prices[i]
        if p <= 0:
            continue

        if p > hi:
            hi = p
            hi_i = i
        if p < lo:
            lo = p
            lo_i = i

        # decide dirección
        if direction == 0:
            # si sube desde lo o baja desde hi lo suficiente, arranca
            if lo > 0 and (p - lo) / lo >= pct:
                direction = 1
                pivots.append(Pivot(idx=lo_i, price=lo, kind="L"))
                hi = p
                hi_i = i
            elif hi > 0 and (hi - p) / hi >= pct:
                direction = -1
                pivots.append(Pivot(idx=hi_i, price=hi, kind="H"))
                lo = p
                lo_i = i
            continue

        if direction == 1:
            # venimos subiendo: si cae desde hi >= pct => pivot high
            if hi > 0 and (hi - p) / hi >= pct:
                pivots.append(Pivot(idx=hi_i, price=hi, kind="H"))
                direction = -1
                lo = p
                lo_i = i
        else:
            # venimos bajando: si sube desde lo >= pct => pivot low
            if lo > 0 and (p - lo) / lo >= pct:
                pivots.append(Pivot(idx=lo_i, price=lo, kind="L"))
                direction = 1
                hi = p
                hi_i = i

    # cerrar último extremo
    if direction == 1:
        pivots.append(Pivot(idx=hi_i, price=hi, kind="H"))
    elif direction == -1:
        pivots.append(Pivot(idx=lo_i, price=lo, kind="L"))

    # limpieza: pivots alternados
    cleaned: List[Pivot] = []
    for pv in pivots:
        if not cleaned:
            cleaned.append(pv)
            continue
        if cleaned[-1].kind == pv.kind:
            # si es mismo tipo, nos quedamos con el más extremo
            if pv.kind == "H" and pv.price >= cleaned[-1].price:
                cleaned[-1] = pv
            elif pv.kind == "L" and pv.price <= cleaned[-1].price:
                cleaned[-1] = pv
        else:
            cleaned.append(pv)

    return cleaned


# =============================================================================
# Medición: retroceso vs impulso (ratios fibo)
# =============================================================================

def _measure_swings(prices: List[float], pivots: List[Pivot], lookahead: int) -> List[float]:
    """
    Para cada impulso (L->H o H->L) mide cuánto retrocede en las siguientes lookahead velas.
    Devuelve ratios:
      - impulso alcista: ratio = (H - min_after) / (H - L)
      - impulso bajista: ratio = (max_after - L) / (H - L)
    Ratio:
      0.618 ~ llega a 0.618
      0.786 ~ llega a 0.786
      1.0   ~ llega al 100
      >1.0  ~ overshoot (stop-hunt)
    """
    if len(pivots) < 3:
        return []

    ratios: List[float] = []
    n = len(prices)

    for i in range(len(pivots) - 1):
        a = pivots[i]
        b = pivots[i + 1]
        if a.price <= 0 or b.price <= 0:
            continue

        start = a.price
        end = b.price
        idx_end = b.idx

        if idx_end < 0 or idx_end >= n:
            continue

        rng = abs(end - start)
        if rng <= 0:
            continue

        j0 = idx_end + 1
        j1 = min(n, idx_end + 1 + max(5, lookahead))
        if j0 >= j1:
            continue

        window = prices[j0:j1]
        window = [x for x in window if x > 0]
        if not window:
            continue

        # Alcista: L->H
        if a.kind == "L" and b.kind == "H":
            min_after = min(window)
            ratio = (end - min_after) / rng
            ratios.append(float(ratio))

        # Bajista: H->L
        if a.kind == "H" and b.kind == "L":
            max_after = max(window)
            ratio = (max_after - end) / rng
            ratios.append(float(ratio))

    return ratios


def compute_fibo_stats(
    candles: List[Dict[str, Any]],
    zigzag_pct: float = DEFAULT_ZIGZAG_PCT,
    lookahead: int = DEFAULT_LOOKAHEAD,
) -> Dict[str, Any]:
    prices = _closes(candles)
    prices = [p for p in prices if p > 0]
    if len(prices) < 80:
        return {
            "ok": True,
            "n_swings": 0,
            "low_conf": True,
            "note": "pocas velas para estadística",
        }

    pivots = _zigzag_pivots(prices, pct=zigzag_pct)
    ratios = _measure_swings(prices, pivots, lookahead=lookahead)

    n = len(ratios)
    if n == 0:
        return {
            "ok": True,
            "n_swings": 0,
            "low_conf": True,
            "note": "sin swings medibles",
        }

    def prob_ge(x: float) -> float:
        return round(sum(1 for r in ratios if r >= x) / float(n), 4)

    p618 = prob_ge(0.618)
    p786 = prob_ge(0.786)
    p100 = prob_ge(1.0)
    p_ov = round(sum(1 for r in ratios if r > 1.0) / float(n), 4)

    med = round(_median(ratios), 4)

    bias_hint = "neutral"
    if p_ov >= 0.45:
        bias_hint = "overshoot_frecuente"
    elif p786 >= 0.60 and p_ov < 0.35:
        bias_hint = "respeta_zona_profunda"
    elif p618 < 0.40:
        bias_hint = "tendencia_fuerte_pullbacks_poco_profundos"

    return {
        "ok": True,
        "n_swings": n,
        "low_conf": bool(n < MIN_SWINGS_FOR_CONF),
        "zigzag_pct": float(zigzag_pct),
        "lookahead": int(lookahead),
        "p_reach_0_618": p618,
        "p_reach_0_786": p786,
        "p_reach_1_0": p100,
        "p_overshoot_gt_1_0": p_ov,
        "median_retracement": med,
        "bias_hint": bias_hint,
    }


# =============================================================================
# Store (in-memory + opcional JSON)
# =============================================================================

_CACHE: Dict[str, Dict[str, Any]] = {}


def _k(symbol: str, tf: str) -> str:
    return f"{symbol}::{tf}"


def load_store() -> None:
    global _CACHE
    if not PERSIST_PATH:
        return
    try:
        if os.path.exists(PERSIST_PATH):
            with open(PERSIST_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                _CACHE = data
    except Exception:
        # store opcional, si falla no rompe nada
        pass


def save_store() -> None:
    if not PERSIST_PATH:
        return
    try:
        os.makedirs(os.path.dirname(PERSIST_PATH), exist_ok=True)
        with open(PERSIST_PATH, "w", encoding="utf-8") as f:
            json.dump(_CACHE, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def update_stats(symbol: str, tf: str, candles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calcula stats con velas actuales y actualiza cache.
    """
    st = compute_fibo_stats(candles)
    st["ts_ms"] = _now_ms()
    st["symbol"] = symbol
    st["tf"] = tf

    key = _k(symbol, tf)
    _CACHE[key] = st
    save_store()
    return st


def get_stats(symbol: str, tf: str) -> Optional[Dict[str, Any]]:
    return _CACHE.get(_k(symbol, tf))
