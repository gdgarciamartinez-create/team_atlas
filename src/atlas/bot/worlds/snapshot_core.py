# src/atlas/bot/worlds/snapshot_core.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Optional
import time


# ---------- utils ----------
def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _candle_ohlc(c: Dict[str, Any]) -> Tuple[float, float, float, float]:
    # Acepta formatos tipo MT5 o fake:
    # - open/high/low/close
    # - o/h/l/c
    o = _safe_float(c.get("open", c.get("o")))
    h = _safe_float(c.get("high", c.get("h")))
    l = _safe_float(c.get("low", c.get("l")))
    cl = _safe_float(c.get("close", c.get("c")))
    return o, h, l, cl


def _atr(candles: List[Dict[str, Any]], period: int = 14) -> float:
    if len(candles) < period + 2:
        return 0.0
    trs: List[float] = []
    start = max(1, len(candles) - (period + 1))
    for i in range(start, len(candles)):
        prev = candles[i - 1]
        cur = candles[i]
        _, _, _, pc = _candle_ohlc(prev)
        _, h, l, _ = _candle_ohlc(cur)
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)
    if not trs:
        return 0.0
    return sum(trs[-period:]) / float(min(period, len(trs)))


def _swing_hi_lo(candles: List[Dict[str, Any]], lookback: int = 120) -> Tuple[float, float]:
    if not candles:
        return 0.0, 0.0
    chunk = candles[-min(lookback, len(candles)) :]
    highs = [_safe_float(c.get("high", c.get("h"))) for c in chunk]
    lows = [_safe_float(c.get("low", c.get("l"))) for c in chunk]
    return (max(highs) if highs else 0.0), (min(lows) if lows else 0.0)


def _trend_side(candles: List[Dict[str, Any]], lookback: int = 50) -> str:
    # Informativo (no ejecuta). Solo para orientar tablero.
    if len(candles) < 10:
        return "WAIT"
    chunk = candles[-min(lookback, len(candles)) :]
    closes = [_safe_float(c.get("close", c.get("c"))) for c in chunk]
    if len(closes) < 5:
        return "WAIT"
    drift = closes[-1] - closes[0]
    if drift > 0:
        return "BUY"
    if drift < 0:
        return "SELL"
    return "WAIT"


def _fibo_zone_from_swing(hi: float, lo: float, side: str, fibo_low: float, fibo_high: float) -> Tuple[float, float]:
    if hi <= 0 or lo <= 0 or hi == lo:
        return 0.0, 0.0
    rng = hi - lo
    if rng <= 0:
        return 0.0, 0.0

    if side == "BUY":
        z1 = hi - rng * fibo_low
        z2 = hi - rng * fibo_high
        return min(z1, z2), max(z1, z2)

    if side == "SELL":
        z1 = lo + rng * fibo_low
        z2 = lo + rng * fibo_high
        return min(z1, z2), max(z1, z2)

    return 0.0, 0.0


def _in_zone(price: float, zlo: float, zhi: float) -> bool:
    if zlo == 0.0 and zhi == 0.0:
        return False
    lo = min(zlo, zhi)
    hi = max(zlo, zhi)
    return lo <= price <= hi


def _two_close_signal(candles: List[Dict[str, Any]], side: str, zlo: float, zhi: float) -> bool:
    # “GATILLO”: 2 cierres consecutivos fuera de la zona en dirección
    if len(candles) < 3:
        return False
    _, _, _, cl1 = _candle_ohlc(candles[-2])
    _, _, _, cl2 = _candle_ohlc(candles[-1])

    if side == "BUY":
        return cl1 > zhi and cl2 > zhi
    if side == "SELL":
        return cl1 < zlo and cl2 < zlo
    return False


def _light_for_state(state: str) -> str:
    s = (state or "").upper().strip()
    if s == "GATILLO":
        return "GREEN"
    if s == "ZONA":
        return "YELLOW"
    if s == "ERROR":
        return "RED"
    return "GRAY"


# ---------- AB ----------
@dataclass
class ABResult:
    A_atr: float
    B_buffer: float
    AB: float
    price_ref: float
    n: int
    meta: Dict[str, Any]


def calc_A_B(
    candles: List[Dict[str, Any]],
    atr_period: int,
    b_price_pct: float,
    b_atr_mult: float,
) -> ABResult:
    n = len(candles)
    if n < 5:
        return ABResult(0.0, 0.0, 0.0, 0.0, n, {"reason": "no_candles_loaded"})

    _, _, _, last_close = _candle_ohlc(candles[-1])
    price_ref = last_close
    A = _atr(candles, period=atr_period)

    b_by_price = abs(price_ref) * float(b_price_pct)
    b_by_atr = float(A) * float(b_atr_mult)
    B = max(b_by_price, b_by_atr)

    return ABResult(
        A_atr=A,
        B_buffer=B,
        AB=A + B,
        price_ref=price_ref,
        n=n,
        meta={
            "atr_period": atr_period,
            "b_price_pct": b_price_pct,
            "b_atr_mult": b_atr_mult,
            "b_by_price": b_by_price,
            "b_by_atr": b_by_atr,
        },
    )


# ---------- Plan cache (persistencia real) ----------
@dataclass
class Plan:
    state: str  # WAIT | ZONA | GATILLO
    side: str   # BUY | SELL | WAIT
    zlo: float
    zhi: float
    hi: float
    lo: float
    created_ms: int
    updated_ms: int
    note: str = ""


_PLAN_CACHE: Dict[str, Plan] = {}  # key = f"{world}|{symbol}|{tf}"


def _now_ms() -> int:
    return int(time.time() * 1000)


def _key(world: str, symbol: str, tf: str) -> str:
    return f"{(world or '').upper()}|{symbol}|{(tf or '').upper()}"


def invalidate_plan(world: str, symbol: str, tf: str) -> None:
    _PLAN_CACHE.pop(_key(world, symbol, tf), None)


def get_plan(world: str, symbol: str, tf: str) -> Optional[Plan]:
    return _PLAN_CACHE.get(_key(world, symbol, tf))


def set_plan(world: str, symbol: str, tf: str, plan: Plan) -> None:
    _PLAN_CACHE[_key(world, symbol, tf)] = plan


# ---------- scoring ----------
def compute_score(
    state: str,
    side: str,
    in_zone: bool,
    has_gatillo: bool,
    ab: ABResult,
) -> Tuple[int, str]:
    score = 10
    why: List[str] = []

    if side in ("BUY", "SELL"):
        score += 10
        why.append("side definido")

    if in_zone:
        score += 25
        why.append("en zona")

    st = (state or "").upper().strip()
    if st == "ZONA":
        score += 10
        why.append("plan activo")
    if st == "GATILLO" or has_gatillo:
        score += 35
        why.append("gatillo")

    vol = False
    if ab.price_ref and ab.A_atr:
        rel = ab.A_atr / ab.price_ref
        if rel >= 0.002:
            vol = True
            score += 10
            why.append("volátil")

    score = max(0, min(100, score))
    note = ", ".join(why) if why else "esperando"
    if vol and "volátil" not in note:
        note += " • volátil"
    return score, note


# ---------- analyzer persistente ----------
def analyze_with_persistence(
    *,
    world: str,
    symbol: str,
    tf: str,
    candles: List[Dict[str, Any]],
    fibo_low: float,
    fibo_high: float,
    atr_period: int,
    b_price_pct: float,
    b_atr_mult: float,
    lookback_swing: int = 160,
) -> Dict[str, Any]:
    if not candles:
        ab0 = calc_A_B([], atr_period, b_price_pct, b_atr_mult)
        return {
            "state": "WAIT",
            "side": "WAIT",
            "price": 0.0,
            "zlo": 0.0,
            "zhi": 0.0,
            "hi": 0.0,
            "lo": 0.0,
            "ab": ab0,
            "light": "GRAY",
            "score": 0,
            "note": "sin velas",
            "plan_frozen": False,
        }

    _, _, _, price = _candle_ohlc(candles[-1])

    plan = get_plan(world, symbol, tf)
    side_live = _trend_side(candles)

    hi_live, lo_live = _swing_hi_lo(candles, lookback=min(lookback_swing, len(candles)))
    zlo_live, zhi_live = _fibo_zone_from_swing(hi_live, lo_live, side_live, fibo_low, fibo_high)

    ab = calc_A_B(candles, atr_period, b_price_pct, b_atr_mult)
    now = _now_ms()

    if plan is None:
        in_zone_live = _in_zone(price, zlo_live, zhi_live)
        if in_zone_live and side_live in ("BUY", "SELL") and zlo_live and zhi_live:
            plan = Plan(
                state="ZONA",
                side=side_live,
                zlo=zlo_live,
                zhi=zhi_live,
                hi=hi_live,
                lo=lo_live,
                created_ms=now,
                updated_ms=now,
                note=f"precio dentro zona {fibo_low:.3f}–{fibo_high:.3f}",
            )
            set_plan(world, symbol, tf, plan)
        else:
            score, note2 = compute_score("WAIT", side_live, in_zone_live, False, ab)
            return {
                "state": "WAIT",
                "side": side_live,
                "price": price,
                "zlo": zlo_live,
                "zhi": zhi_live,
                "hi": hi_live,
                "lo": lo_live,
                "ab": ab,
                "light": _light_for_state("WAIT"),
                "score": score,
                "note": note2,
                "plan_frozen": False,
            }

    zlo = plan.zlo
    zhi = plan.zhi
    side = plan.side
    in_zone = _in_zone(price, zlo, zhi)

    buffer = max(ab.B_buffer, 0.0)
    invalid = False
    if side == "BUY" and price < (min(zlo, zhi) - buffer):
        invalid = True
    if side == "SELL" and price > (max(zlo, zhi) + buffer):
        invalid = True

    if invalid:
        invalidate_plan(world, symbol, tf)
        score, _ = compute_score("WAIT", side_live, _in_zone(price, zlo_live, zhi_live), False, ab)
        return {
            "state": "WAIT",
            "side": side_live,
            "price": price,
            "zlo": zlo_live,
            "zhi": zhi_live,
            "hi": hi_live,
            "lo": lo_live,
            "ab": ab,
            "light": _light_for_state("WAIT"),
            "score": score,
            "note": "plan invalidado → reset",
            "plan_frozen": False,
        }

    has_gatillo = _two_close_signal(candles, side, min(zlo, zhi), max(zlo, zhi))
    if plan.state == "ZONA" and has_gatillo:
        plan.state = "GATILLO"
        plan.updated_ms = now
        plan.note = "2 cierres → GATILLO (listo ejecución)"
        set_plan(world, symbol, tf, plan)

    state = plan.state
    score, note2 = compute_score(state, side, in_zone, has_gatillo, ab)
    note_final = plan.note or note2

    return {
        "state": state,
        "side": side,
        "price": price,
        "zlo": min(zlo, zhi),
        "zhi": max(zlo, zhi),
        "hi": plan.hi,
        "lo": plan.lo,
        "ab": ab,
        "light": _light_for_state(state),
        "score": score,
        "note": note_final,
        "plan_frozen": True,
        "plan_created_ms": plan.created_ms,
        "plan_updated_ms": plan.updated_ms,
    }