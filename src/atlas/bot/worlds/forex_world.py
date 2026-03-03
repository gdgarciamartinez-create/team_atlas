# src/atlas/bot/worlds/forex_world.py
from __future__ import annotations

import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple

from atlas.bot.worlds.feed import get_feed_with_meta


# =============================================================================
# Config "profesional" (estable)
# =============================================================================

RISK_PERCENT_DEFAULT = 1.5  # modo agresivo (paper / auditoría)
RISK_CCY_DEFAULT = "USD"

STATE_WAIT = "WAIT"
STATE_WAIT_GATILLO = "WAIT_GATILLO"
STATE_SIGNAL = "SIGNAL"


# =============================================================================
# Estado persistente (congelación de plan / señal)
# =============================================================================

@dataclass
class FrozenPlan:
    symbol: str
    tf: str
    side: str  # BUY / SELL
    zone_lo: float
    zone_hi: float
    created_ts_ms: int
    reason: str
    fib: Dict[str, Any]
    ab: Dict[str, Any]


@dataclass
class FrozenSignal:
    symbol: str
    tf: str
    side: str
    entry: float
    sl: float
    tp1: float
    tp2: float
    created_ts_ms: int
    reason: str


@dataclass
class SlotState:
    state: str  # WAIT | WAIT_GATILLO | SIGNAL
    plan: Optional[FrozenPlan] = None
    signal: Optional[FrozenSignal] = None
    last_note: str = ""


# clave: (symbol, tf)
_SLOTS: Dict[Tuple[str, str], SlotState] = {}


# =============================================================================
# Helpers
# =============================================================================

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


def _simple_atr(candles: List[Dict[str, Any]], period: int = 14) -> float:
    if len(candles) < 2:
        return 0.0
    n = min(period, len(candles) - 1)
    trs: List[float] = []
    for i in range(-n, 0):
        _, h, l, _ = _candle_ohlc(candles[i])
        _, _, _, prev_c = _candle_ohlc(candles[i - 1])
        tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
        trs.append(tr)
    if not trs:
        return 0.0
    return sum(trs) / float(len(trs))


def _swing_hi_lo(candles: List[Dict[str, Any]], lookback: int = 160) -> Tuple[float, float]:
    if not candles:
        return 0.0, 0.0
    lb = max(30, min(lookback, len(candles)))
    w = candles[-lb:]
    hi = max(_safe_float(x.get("h"), 0.0) for x in w)
    lo = min(_safe_float(x.get("l"), 0.0) for x in w)
    return hi, lo


def _trend_side(candles: List[Dict[str, Any]]) -> str:
    """
    Sesgo simple y estable:
    - compara cierre actual vs promedio de últimos 60 cierres.
    """
    if len(candles) < 80:
        return "WAIT"
    closes = [_safe_float(c.get("c"), 0.0) for c in candles[-60:]]
    if not closes:
        return "WAIT"
    avg = sum(closes) / float(len(closes))
    last = closes[-1]
    return "BUY" if last >= avg else "SELL"


def _fibo_zone_from_swing(hi: float, lo: float, side: str) -> Tuple[float, float, Dict[str, Any]]:
    """
    Zona de decisión: 0.618–0.786 (sin 0.79).
    BUY: retroceso desde hi hacia lo
    SELL: retroceso desde lo hacia hi
    """
    rng = max(hi - lo, 0.0)
    if rng <= 0:
        fib = {"hi": hi, "lo": lo, "rng": rng, "fibo_618": 0.0, "fibo_786": 0.0, "zone_lo": 0.0, "zone_hi": 0.0}
        return 0.0, 0.0, fib

    if side == "BUY":
        fib_618 = hi - 0.618 * rng
        fib_786 = hi - 0.786 * rng
        zlo, zhi = sorted([fib_618, fib_786])
    elif side == "SELL":
        fib_618 = lo + 0.618 * rng
        fib_786 = lo + 0.786 * rng
        zlo, zhi = sorted([fib_618, fib_786])
    else:
        fib = {"hi": hi, "lo": lo, "rng": rng, "fibo_618": 0.0, "fibo_786": 0.0, "zone_lo": 0.0, "zone_hi": 0.0}
        return 0.0, 0.0, fib

    fib = {
        "hi": hi,
        "lo": lo,
        "rng": rng,
        "fibo_618": fib_618,
        "fibo_786": fib_786,
        "zone_lo": zlo,
        "zone_hi": zhi,
        "optimal": 0.786,  # referencia conceptual (no nivel 0.79)
    }
    return zlo, zhi, fib


def _in_zone(price: float, zlo: float, zhi: float) -> bool:
    if zlo <= 0 and zhi <= 0:
        return False
    lo, hi = sorted([zlo, zhi])
    return lo <= price <= hi


def _two_close_accepts_outside(candles: List[Dict[str, Any]], zlo: float, zhi: float, side: str) -> bool:
    """
    Filtro duro:
    - BUY: 2 cierres por debajo de zona => aceptación bajista => invalida
    - SELL: 2 cierres por encima de zona => aceptación alcista => invalida
    """
    if len(candles) < 3:
        return False
    lo, hi = sorted([zlo, zhi])
    c1 = _safe_float(candles[-1].get("c"), 0.0)
    c2 = _safe_float(candles[-2].get("c"), 0.0)
    if side == "BUY":
        return (c1 < lo) and (c2 < lo)
    if side == "SELL":
        return (c1 > hi) and (c2 > hi)
    return False


def _mk_light(state: str) -> str:
    if state == STATE_SIGNAL:
        return "GREEN"
    if state == STATE_WAIT_GATILLO:
        return "YELLOW"
    return "GRAY"


def _mk_score(state: str, note: str) -> int:
    base = 25 if state == STATE_WAIT else 55 if state == STATE_WAIT_GATILLO else 85
    if "invalid" in (note or "").lower():
        return 10
    return base


def _calc_A_B(candles: List[Dict[str, Any]], atr_period: int, b_price_pct: float, b_atr_mult: float) -> Dict[str, Any]:
    """
    A/B = buffers que usamos para:
    - rango mínimo
    - buffer de barrida (sweep buffer)
    Mantiene consistencia y no mete magia.
    """
    atr = _simple_atr(candles, period=atr_period) if candles else 0.0
    price = _last_close(candles) if candles else 0.0

    # A = buffer por % de precio (mínimo) y ATR (componente dinámico)
    a_price = abs(price) * float(b_price_pct)
    a_atr = atr * float(b_atr_mult)

    A = max(a_price, a_atr, 0.0)
    # B = rango mínimo “operable” (evitar micro-rango)
    B = max(atr * 1.2, 0.0)  # estable

    return {
        "atr": float(atr),
        "price": float(price),
        "A_buffer": float(A),
        "B_range_min": float(B),
        "b_price_pct": float(b_price_pct),
        "b_atr_mult": float(b_atr_mult),
        "atr_period": int(atr_period),
    }


# =============================================================================
# Core
# =============================================================================

def build_forex_world(
    symbol: str,
    tf: str,
    count: int = 220,
    # ATR y buffers
    atr_period: int = 14,
    b_price_pct: float = 0.0005,  # 0.05%
    b_atr_mult: float = 0.2,
    # SL/TP (modo agresivo paper)
    sl_atr_mult: float = 1.2,
    tp1_r: float = 1.0,
    tp2_r: float = 2.0,
    # riesgo (para bitácora / UI; ejecución real viene después)
    risk_percent: float = RISK_PERCENT_DEFAULT,
    risk_ccy: str = RISK_CCY_DEFAULT,
) -> Dict[str, Any]:
    """
    FOREX:
    - WAIT: aún no toca zona 0.618–0.786
    - WAIT_GATILLO: plan congelado (zona + lado)
    - SIGNAL: entry/sl/tp congelados con confirmación

    Gatillo "institucional" (estable):
    - Estar en WAIT_GATILLO
    - y 2 cierres confirmatorios fuera de zona a favor:
        BUY: 2 cierres > zone_hi
        SELL: 2 cierres < zone_lo
    """

    candles, meta = get_feed_with_meta(symbol=symbol, tf=tf, n=count)

    if not candles:
        ab0 = _calc_A_B([], atr_period, b_price_pct, b_atr_mult)
        return _snapshot(
            world="FOREX",
            symbol=symbol,
            tf=tf,
            candles=[],
            meta=meta or {},
            state=STATE_WAIT,
            side="WAIT",
            price=0.0,
            zone=(0.0, 0.0),
            note="sin velas",
            score=0,
            light="GRAY",
            plan=None,
            signal=None,
            fib={},
            ab=ab0,
            params=_params(atr_period, b_price_pct, b_atr_mult, sl_atr_mult, tp1_r, tp2_r, risk_percent, risk_ccy),
        )

    price = _last_close(candles)
    side = _trend_side(candles)
    hi, lo = _swing_hi_lo(candles, lookback=min(220, max(120, count)))
    zlo, zhi, fib = _fibo_zone_from_swing(hi, lo, side)
    ab = _calc_A_B(candles, atr_period, b_price_pct, b_atr_mult)

    key = (symbol, tf)
    slot = _SLOTS.get(key)
    if slot is None:
        slot = SlotState(state=STATE_WAIT, plan=None, signal=None, last_note="")
        _SLOTS[key] = slot

    # 1) invalidación dura por aceptación contraria (si hay plan)
    if slot.plan is not None:
        pl = slot.plan
        if _two_close_accepts_outside(candles, pl.zone_lo, pl.zone_hi, pl.side):
            slot.state = STATE_WAIT
            slot.plan = None
            slot.signal = None
            slot.last_note = "invalidación: 2 cierres fuera (aceptación contraria)"

    # 2) si está en SIGNAL, mantener congelado
    if slot.state == STATE_SIGNAL and slot.signal is not None:
        note = "señal congelada (paper/auditoría)"
        light = _mk_light(slot.state)
        score = _mk_score(slot.state, note)
        zone = (slot.plan.zone_lo, slot.plan.zone_hi) if slot.plan else (zlo, zhi)
        return _snapshot(
            world="FOREX",
            symbol=symbol,
            tf=tf,
            candles=candles,
            meta=meta or {},
            state=slot.state,
            side=slot.signal.side,
            price=price,
            zone=zone,
            note=note,
            score=score,
            light=light,
            plan=asdict(slot.plan) if slot.plan else None,
            signal=asdict(slot.signal),
            fib=fib,
            ab=ab,
            params=_params(atr_period, b_price_pct, b_atr_mult, sl_atr_mult, tp1_r, tp2_r, risk_percent, risk_ccy),
        )

    # 3) si está en WAIT, congelar plan al entrar en zona
    if slot.state == STATE_WAIT:
        if side in ("BUY", "SELL") and _in_zone(price, zlo, zhi):
            slot.state = STATE_WAIT_GATILLO
            slot.plan = FrozenPlan(
                symbol=symbol,
                tf=tf,
                side=side,
                zone_lo=min(zlo, zhi),
                zone_hi=max(zlo, zhi),
                created_ts_ms=_now_ms(),
                reason="precio dentro de zona 0.618–0.786 (foco 0.786)",
                fib=fib,
                ab=ab,
            )
            slot.signal = None
            slot.last_note = "plan congelado: esperando gatillo"
        else:
            slot.last_note = "esperando zona"

    # 4) si está en WAIT_GATILLO, mantener plan y buscar gatillo
    if slot.state == STATE_WAIT_GATILLO and slot.plan is not None:
        pl = slot.plan

        # si cambia el lado dominante, resetea (evita confusión)
        if side in ("BUY", "SELL") and side != pl.side:
            slot.state = STATE_WAIT
            slot.plan = None
            slot.signal = None
            slot.last_note = "reset: cambió el sesgo"
        else:
            c1 = _safe_float(candles[-1].get("c"), 0.0)
            c2 = _safe_float(candles[-2].get("c"), 0.0)

            if pl.side == "BUY":
                fired = (c1 > pl.zone_hi) and (c2 > pl.zone_hi)
            else:
                fired = (c1 < pl.zone_lo) and (c2 < pl.zone_lo)

            if fired:
                atr = _simple_atr(candles, period=atr_period)
                sl_dist = max(atr * sl_atr_mult, abs(pl.zone_hi - pl.zone_lo) * 0.8, atr * 0.5)

                entry = float(c1)  # entry al cierre confirmatorio (robusto)
                if pl.side == "BUY":
                    sl = float(min(pl.zone_lo, pl.zone_hi) - sl_dist)
                    r = max(entry - sl, 0.0)
                    tp1 = float(entry + (r * tp1_r))
                    tp2 = float(entry + (r * tp2_r))
                else:
                    sl = float(max(pl.zone_lo, pl.zone_hi) + sl_dist)
                    r = max(sl - entry, 0.0)
                    tp1 = float(entry - (r * tp1_r))
                    tp2 = float(entry - (r * tp2_r))

                slot.signal = FrozenSignal(
                    symbol=symbol,
                    tf=tf,
                    side=pl.side,
                    entry=float(entry),
                    sl=float(sl),
                    tp1=float(tp1),
                    tp2=float(tp2),
                    created_ts_ms=_now_ms(),
                    reason="gatillo: 2 cierres confirmatorios fuera de zona a favor",
                )
                slot.state = STATE_SIGNAL
                slot.last_note = "SIGNAL: armado y congelado"
            else:
                slot.last_note = "esperando gatillo (plan congelado)"

    # 5) snapshot final
    note = slot.last_note or "ok"
    light = _mk_light(slot.state)
    score = _mk_score(slot.state, note)

    zone = (zlo, zhi)
    if slot.plan is not None:
        zone = (slot.plan.zone_lo, slot.plan.zone_hi)

    out_side = side if side in ("BUY", "SELL") else "WAIT"
    if slot.signal is not None:
        out_side = slot.signal.side

    return _snapshot(
        world="FOREX",
        symbol=symbol,
        tf=tf,
        candles=candles,
        meta=meta or {},
        state=slot.state,
        side=out_side,
        price=price,
        zone=zone,
        note=note,
        score=score,
        light=light,
        plan=asdict(slot.plan) if slot.plan else None,
        signal=asdict(slot.signal) if slot.signal else None,
        fib=fib,
        ab=ab,
        params=_params(atr_period, b_price_pct, b_atr_mult, sl_atr_mult, tp1_r, tp2_r, risk_percent, risk_ccy),
    )


# =============================================================================
# Snapshot formatting (compat UI)
# =============================================================================

def _params(
    atr_period: int,
    b_price_pct: float,
    b_atr_mult: float,
    sl_atr_mult: float,
    tp1_r: float,
    tp2_r: float,
    risk_percent: float,
    risk_ccy: str,
) -> Dict[str, Any]:
    return {
        "atr_period": int(atr_period),
        "b_price_pct": float(b_price_pct),
        "b_atr_mult": float(b_atr_mult),
        "sl_atr_mult": float(sl_atr_mult),
        "tp1_r": float(tp1_r),
        "tp2_r": float(tp2_r),
        "risk_percent": float(risk_percent),
        "risk_ccy": str(risk_ccy),
        "mode": "AGGRESSIVE",
    }


def _snapshot(
    world: str,
    symbol: str,
    tf: str,
    candles: List[Dict[str, Any]],
    meta: Dict[str, Any],
    state: str,
    side: str,
    price: float,
    zone: Tuple[float, float],
    note: str,
    score: int,
    light: str,
    plan: Optional[Dict[str, Any]],
    signal: Optional[Dict[str, Any]],
    fib: Dict[str, Any],
    ab: Dict[str, Any],
    params: Dict[str, Any],
) -> Dict[str, Any]:
    # trade plano para bitácora (auto)
    trade: Optional[Dict[str, Any]] = None
    entry = sl = tp = 0.0

    if state == STATE_SIGNAL and isinstance(signal, dict):
        entry = _safe_float(signal.get("entry"), 0.0)
        sl = _safe_float(signal.get("sl"), 0.0)
        tp = _safe_float(signal.get("tp2"), 0.0)  # tp principal = tp2
        trade = {
            "side": side,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "tp1": _safe_float(signal.get("tp1"), 0.0),
            "tp2": _safe_float(signal.get("tp2"), 0.0),
            "risk_percent": _safe_float(params.get("risk_percent"), RISK_PERCENT_DEFAULT),
            "risk_ccy": str(params.get("risk_ccy", RISK_CCY_DEFAULT)),
        }

    z0, z1 = float(zone[0]), float(zone[1])

    return {
        "ok": True,
        "world": world,
        "symbol": symbol,
        "tf": tf,
        "ts_ms": _now_ms(),
        "candles": candles or [],
        "meta": meta or {},
        "state": state,
        "side": side,
        "price": float(price),
        "zone": (z0, z1),
        "note": note,
        "score": int(score),
        "light": light,
        "plan": plan,
        "signal": signal,
        "trade": trade,
        "entry": float(entry),
        "sl": float(sl),
        "tp": float(tp),
        "fib": fib or {},
        "ab": ab or {},
        "params": params or {},
        "analysis": {
            "state": state,
            "side": side,
            "zone": {"lo": z0, "hi": z1},
            "plan_frozen": bool(plan is not None),
            "signal_frozen": bool(signal is not None),
            "risk": {"percent": params.get("risk_percent"), "ccy": params.get("risk_ccy")},
        },
        "ui": {
            "rows": [
                {"k": "Estado", "v": state},
                {"k": "Lado", "v": side},
                {"k": "Precio", "v": float(price)},
                {"k": "Zona", "v": f"{z0:.5f} - {z1:.5f}" if abs(z0) < 10 else f"{z0:.2f} - {z1:.2f}"},
                {"k": "Nota", "v": note},
                {"k": "Score", "v": int(score)},
                {"k": "Riesgo", "v": f"{params.get('risk_percent', RISK_PERCENT_DEFAULT)}% {params.get('risk_ccy', RISK_CCY_DEFAULT)}"},
            ]
        },
        "last_error": None,
    }