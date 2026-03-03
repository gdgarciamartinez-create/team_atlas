# src/atlas/bot/analysis/atlas_method.py
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Tuple, Optional

from atlas.bot.analysis.elliott import detect_elliott_pro


def _f(x: Any, d: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return d


def _ohlc(c: Dict[str, Any]) -> Tuple[float, float, float, float]:
    return _f(c.get("o")), _f(c.get("h")), _f(c.get("l")), _f(c.get("c"))


def last_close(candles: List[Dict[str, Any]]) -> float:
    return _f(candles[-1].get("c")) if candles else 0.0


def swing_hi_lo(candles: List[Dict[str, Any]], lookback: int = 160) -> Tuple[float, float]:
    if not candles:
        return 0.0, 0.0
    lb = max(40, min(lookback, len(candles)))
    w = candles[-lb:]
    hi = max(_f(x.get("h")) for x in w)
    lo = min(_f(x.get("l")) for x in w)
    return hi, lo


def simple_atr(candles: List[Dict[str, Any]], period: int = 14) -> float:
    if len(candles) < 3:
        return 0.0
    n = min(period, len(candles) - 1)
    trs: List[float] = []
    for i in range(-n, 0):
        o, h, l, c = _ohlc(candles[i])
        _, _, _, pc = _ohlc(candles[i - 1])
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)
    return sum(trs) / max(len(trs), 1)


def fib_zone_618_786(hi: float, lo: float, side: str) -> Tuple[float, float, Dict[str, Any]]:
    """
    Zona óptima: 0.618 a 0.786 (NO usamos 0.79).
    BUY: retroceso desde hi hacia lo.
    SELL: retroceso desde lo hacia hi.
    """
    rng = max(hi - lo, 0.0)
    if rng <= 0:
        return 0.0, 0.0, {"hi": hi, "lo": lo, "rng": rng, "f618": 0.0, "f786": 0.0}

    if side == "BUY":
        f618 = hi - 0.618 * rng
        f786 = hi - 0.786 * rng
    else:
        f618 = lo + 0.618 * rng
        f786 = lo + 0.786 * rng

    zlo = min(f618, f786)
    zhi = max(f618, f786)
    meta = {"hi": hi, "lo": lo, "rng": rng, "f618": f618, "f786": f786, "zone_lo": zlo, "zone_hi": zhi}
    return zlo, zhi, meta


def in_zone(price: float, zlo: float, zhi: float) -> bool:
    lo = min(zlo, zhi)
    hi = max(zlo, zhi)
    return (lo > 0 and hi > 0 and lo <= price <= hi)


def trend_side_simple(candles: List[Dict[str, Any]], n: int = 60) -> str:
    """
    Lectura simple de sesgo:
    - si el cierre actual está por encima del promedio → BUY
    - si está por debajo → SELL
    """
    if len(candles) < max(30, n):
        return "WAIT"
    closes = [_f(c.get("c")) for c in candles[-n:]]
    avg = sum(closes) / max(len(closes), 1)
    last = closes[-1]
    if last >= avg:
        return "BUY"
    return "SELL"


def two_close_confirm_outside_zone(candles: List[Dict[str, Any]], zlo: float, zhi: float, side: str) -> bool:
    """
    Gatillo institucional robusto:
    BUY: 2 cierres por arriba de zone_hi
    SELL: 2 cierres por abajo de zone_lo
    """
    if len(candles) < 3:
        return False
    c1 = _f(candles[-1].get("c"))
    c2 = _f(candles[-2].get("c"))
    lo = min(zlo, zhi)
    hi = max(zlo, zhi)
    if side == "BUY":
        return (c1 > hi) and (c2 > hi)
    if side == "SELL":
        return (c1 < lo) and (c2 < lo)
    return False


def two_close_accepts_against(candles: List[Dict[str, Any]], zlo: float, zhi: float, side: str) -> bool:
    """
    Regla dura (invalidación por aceptación contraria):
    BUY: 2 cierres por debajo de zone_lo
    SELL: 2 cierres por encima de zone_hi
    """
    if len(candles) < 3:
        return False
    c1 = _f(candles[-1].get("c"))
    c2 = _f(candles[-2].get("c"))
    lo = min(zlo, zhi)
    hi = max(zlo, zhi)
    if side == "BUY":
        return (c1 < lo) and (c2 < lo)
    if side == "SELL":
        return (c1 > hi) and (c2 > hi)
    return False


def atlas_score(side: str, price: float, zlo: float, zhi: float, ell: Dict[str, Any]) -> Tuple[int, str]:
    """
    Score basado en:
    - proximidad / presencia en zona óptima
    - alineación Elliott (no decide, suma o resta)
    """
    score = 20
    note = "estado neutro"

    if side in ("BUY", "SELL") and in_zone(price, zlo, zhi):
        score = 62
        note = "precio en zona óptima (0.618–0.786)"

    # Elliott como filtro
    label = (ell.get("label") or {}) if isinstance(ell, dict) else {}
    mode = str(label.get("mode", "UNKNOWN"))
    stage = str(label.get("stage", "UNKNOWN"))
    conf = float(label.get("confidence", 0) or 0)

    if conf >= 0.55:
        if mode == "IMPULSE" and stage in ("W3", "W5"):
            score += 10
            note += f" + Elliott({stage})"
        elif mode == "CORRECTION" and stage == "ABC":
            score += 6
            note += " + Elliott(ABC)"
        elif mode == "FLAG":
            score += 5
            note += f" + {stage}"
        else:
            score -= 4
            note += " + Elliott mixto"

    score = max(0, min(100, score))
    return score, note


def build_atlas_analysis(candles: List[Dict[str, Any]], atr_period: int = 14) -> Dict[str, Any]:
    """
    Salida compacta y estable para worlds.
    """
    price = last_close(candles)
    side = trend_side_simple(candles)
    hi, lo = swing_hi_lo(candles)
    zlo, zhi, fib = fib_zone_618_786(hi, lo, side if side in ("BUY", "SELL") else "BUY")
    atr = simple_atr(candles, period=atr_period)
    ell = detect_elliott_pro(candles)
    score, note = atlas_score(side, price, zlo, zhi, ell)

    return {
        "price": price,
        "side": side,
        "hi": hi,
        "lo": lo,
        "zone": (zlo, zhi),
        "fib": fib,
        "atr": atr,
        "elliott": ell,
        "score": score,
        "note": note,
    }