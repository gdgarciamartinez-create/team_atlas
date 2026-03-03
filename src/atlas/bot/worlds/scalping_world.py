# src/atlas/bot/worlds/scalping_world.py
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple
import time

from atlas.bot.worlds.feed import get_feed_with_meta


# =============================================================================
# Estado persistente (congelación de plan / señal)
# =============================================================================

@dataclass
class FrozenPlan:
    symbol: str
    tf: str
    side: str  # "BUY" / "SELL"
    zone_lo: float
    zone_hi: float
    created_ts_ms: int
    reason: str
    fib: Dict[str, Any]


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
    state: str  # "WAIT" | "WAIT_GATILLO" | "SIGNAL"
    plan: Optional[FrozenPlan] = None
    signal: Optional[FrozenSignal] = None
    last_note: str = ""


# Clave: (symbol, tf)
_SLOTS: Dict[Tuple[str, str], SlotState] = {}


# =============================================================================
# Helpers velas
# =============================================================================

def _now_ms() -> int:
    return int(time.time() * 1000)


def _candle_ohlc(c: Dict[str, Any]) -> Tuple[float, float, float, float]:
    return float(c.get("o", 0.0)), float(c.get("h", 0.0)), float(c.get("l", 0.0)), float(c.get("c", 0.0))


def _last_close(candles: List[Dict[str, Any]]) -> float:
    if not candles:
        return 0.0
    return float(candles[-1].get("c", 0.0))


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


def _swing_hi_lo(candles: List[Dict[str, Any]], lookback: int = 120) -> Tuple[float, float]:
    if not candles:
        return 0.0, 0.0
    lb = max(20, min(lookback, len(candles)))
    w = candles[-lb:]
    hi = max(float(x.get("h", 0.0)) for x in w)
    lo = min(float(x.get("l", 0.0)) for x in w)
    return hi, lo


def _trend_side(candles: List[Dict[str, Any]]) -> str:
    """
    Side simple:
    - última close vs promedio últimas 30
    """
    if len(candles) < 30:
        return "WAIT"
    closes = [float(c.get("c", 0.0)) for c in candles[-30:]]
    if not closes:
        return "WAIT"
    avg = sum(closes) / float(len(closes))
    last = closes[-1]
    return "BUY" if last >= avg else "SELL"


def _fibo_zone_from_swing(hi: float, lo: float, side: str) -> Tuple[float, float, Dict[str, Any]]:
    """
    Zona de trabajo: 0.618–0.786 del swing, foco 0.786.
    """
    rng = max(hi - lo, 0.0)
    if rng <= 0:
        return 0.0, 0.0, {"hi": hi, "lo": lo, "rng": rng, "fibo_786": 0.0, "fibo_618": 0.0}

    if side == "BUY":
        fib_618 = hi - 0.618 * rng
        fib_786 = hi - 0.786 * rng
        zlo = min(fib_786, fib_618)
        zhi = max(fib_786, fib_618)
    elif side == "SELL":
        fib_618 = lo + 0.618 * rng
        fib_786 = lo + 0.786 * rng
        zlo = min(fib_618, fib_786)
        zhi = max(fib_618, fib_786)
    else:
        return 0.0, 0.0, {"hi": hi, "lo": lo, "rng": rng, "fibo_786": 0.0, "fibo_618": 0.0}

    fib = {
        "hi": hi,
        "lo": lo,
        "rng": rng,
        "fibo_618": fib_618,
        "fibo_786": fib_786,
        "zone_lo": zlo,
        "zone_hi": zhi,
    }
    return zlo, zhi, fib


def _in_zone(price: float, zlo: float, zhi: float) -> bool:
    if zlo <= 0 and zhi <= 0:
        return False
    lo = min(zlo, zhi)
    hi = max(zlo, zhi)
    return lo <= price <= hi


def _two_close_accepts_outside(candles: List[Dict[str, Any]], zlo: float, zhi: float, side: str) -> bool:
    """
    2 cierres consecutivos con aceptación contraria invalidan plan.
    BUY: 2 cierres por debajo de zona_lo
    SELL: 2 cierres por encima de zona_hi
    """
    if len(candles) < 3:
        return False
    lo = min(zlo, zhi)
    hi = max(zlo, zhi)
    c1 = float(candles[-1].get("c", 0.0))
    c2 = float(candles[-2].get("c", 0.0))

    if side == "BUY":
        return (c1 < lo) and (c2 < lo)
    if side == "SELL":
        return (c1 > hi) and (c2 > hi)
    return False


def _mk_light(state: str) -> str:
    if state == "SIGNAL":
        return "GREEN"
    if state == "WAIT_GATILLO":
        return "YELLOW"
    return "GRAY"


def _mk_score(state: str, note: str) -> int:
    base = 25 if state == "WAIT" else 55 if state == "WAIT_GATILLO" else 85
    if "invalid" in note.lower():
        return 10
    return base


# =============================================================================
# Core
# =============================================================================

def build_scalping_world(
    symbol: str,
    tf: str,
    count: int = 220,
    atr_period: int = 14,
    sl_atr_mult: float = 1.2,
    tp1_r: float = 1.0,
    tp2_r: float = 2.0,
) -> Dict[str, Any]:
    """
    SCALPING:
    - WAIT -> WAIT_GATILLO cuando entra a zona
    - WAIT_GATILLO -> SIGNAL cuando hay 2 cierres confirmatorios a favor fuera de zona
    - SIGNAL se mantiene congelado hasta invalidación (2 cierres contrarios)
    """
    candles, meta = get_feed_with_meta(symbol=symbol, tf=tf, n=count)
    if not candles:
        return _snapshot_base(
            symbol=symbol,
            tf=tf,
            candles=[],
            meta=meta or {},
            state="WAIT",
            side="WAIT",
            price=0.0,
            zone=(0.0, 0.0),
            note="sin velas",
            score=0,
            light="GRAY",
            plan=None,
            signal=None,
            params=_params(atr_period, sl_atr_mult, tp1_r, tp2_r),
            fib={},
        )

    price = _last_close(candles)
    side = _trend_side(candles)
    hi, lo = _swing_hi_lo(candles, lookback=min(160, max(60, count)))
    zlo, zhi, fib = _fibo_zone_from_swing(hi, lo, side)

    key = (symbol, tf)
    slot = _SLOTS.get(key)
    if slot is None:
        slot = SlotState(state="WAIT", plan=None, signal=None, last_note="")
        _SLOTS[key] = slot

    # invalidación dura del plan
    if slot.plan is not None:
        pl = slot.plan
        if _two_close_accepts_outside(candles, pl.zone_lo, pl.zone_hi, pl.side):
            slot.state = "WAIT"
            slot.plan = None
            slot.signal = None
            slot.last_note = "invalidación: 2 cierres fuera (aceptación contraria)"

    # si ya hay SIGNAL, mantener congelado
    if slot.state == "SIGNAL" and slot.signal is not None:
        note = "señal congelada"
        light = _mk_light(slot.state)
        score = _mk_score(slot.state, note)
        zone = (slot.plan.zone_lo, slot.plan.zone_hi) if slot.plan else (zlo, zhi)
        return _snapshot_base(
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
            params=_params(atr_period, sl_atr_mult, tp1_r, tp2_r),
            fib=fib,
        )

    # WAIT -> WAIT_GATILLO
    if slot.state == "WAIT":
        if side in ("BUY", "SELL") and _in_zone(price, zlo, zhi):
            slot.state = "WAIT_GATILLO"
            slot.plan = FrozenPlan(
                symbol=symbol,
                tf=tf,
                side=side,
                zone_lo=min(zlo, zhi),
                zone_hi=max(zlo, zhi),
                created_ts_ms=_now_ms(),
                reason="precio dentro de zona (0.618-0.786) foco 0.786",
                fib=fib,
            )
            slot.signal = None
            slot.last_note = "plan congelado: esperando gatillo"
        else:
            slot.last_note = "esperando zona"

    # WAIT_GATILLO -> SIGNAL
    if slot.state == "WAIT_GATILLO" and slot.plan is not None:
        pl = slot.plan

        # si cambia el lado dominante, resetea
        if side in ("BUY", "SELL") and side != pl.side:
            slot.state = "WAIT"
            slot.plan = None
            slot.signal = None
            slot.last_note = "reset: cambió el lado dominante"
        else:
            c1 = float(candles[-1].get("c", 0.0))
            c2 = float(candles[-2].get("c", 0.0))

            if pl.side == "BUY":
                fired = (c1 > pl.zone_hi) and (c2 > pl.zone_hi)
            else:
                fired = (c1 < pl.zone_lo) and (c2 < pl.zone_lo)

            if fired:
                atr = _simple_atr(candles, period=atr_period)
                sl_dist = max(atr * sl_atr_mult, atr * 0.5) if atr > 0 else max(abs(pl.zone_hi - pl.zone_lo) * 0.8, 0.0)

                entry = c1  # entry robusta: cierre confirmatorio
                if pl.side == "BUY":
                    sl = min(pl.zone_lo, pl.zone_hi) - sl_dist
                    r = max(entry - sl, 0.0)
                    tp1 = entry + (r * tp1_r)
                    tp2 = entry + (r * tp2_r)
                else:
                    sl = max(pl.zone_lo, pl.zone_hi) + sl_dist
                    r = max(sl - entry, 0.0)
                    tp1 = entry - (r * tp1_r)
                    tp2 = entry - (r * tp2_r)

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
                slot.state = "SIGNAL"
                slot.last_note = "SIGNAL: armado y congelado"
            else:
                slot.last_note = "esperando gatillo (plan congelado)"

    note = slot.last_note or "ok"
    light = _mk_light(slot.state)
    score = _mk_score(slot.state, note)
    zone = (zlo, zhi)
    if slot.plan is not None:
        zone = (slot.plan.zone_lo, slot.plan.zone_hi)

    final_side = side if side in ("BUY", "SELL") else "WAIT"
    if slot.signal is not None:
        final_side = slot.signal.side

    return _snapshot_base(
        symbol=symbol,
        tf=tf,
        candles=candles,
        meta=meta or {},
        state=slot.state,
        side=final_side,
        price=price,
        zone=zone,
        note=note,
        score=score,
        light=light,
        plan=asdict(slot.plan) if slot.plan else None,
        signal=asdict(slot.signal) if slot.signal else None,
        params=_params(atr_period, sl_atr_mult, tp1_r, tp2_r),
        fib=fib,
    )


# =============================================================================
# Snapshot helpers
# =============================================================================

def _params(atr_period: int, sl_atr_mult: float, tp1_r: float, tp2_r: float) -> Dict[str, Any]:
    return {
        "atr_period": atr_period,
        "sl_atr_mult": sl_atr_mult,
        "tp1_r": tp1_r,
        "tp2_r": tp2_r,
    }


def _snapshot_base(
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
    params: Dict[str, Any],
    fib: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Contrato estándar:
    - Cuando hay SIGNAL: exporta entry/sl/tp en ROOT (tp = tp1)
      para que bitácora abra trade sin depender de subjson.
    """
    entry = 0.0
    sl = 0.0
    tp = 0.0
    trade = None

    if state == "SIGNAL" and isinstance(signal, dict):
        entry = float(signal.get("entry", 0.0) or 0.0)
        sl = float(signal.get("sl", 0.0) or 0.0)
        tp = float(signal.get("tp1", 0.0) or 0.0)  # TP principal = TP1
        if entry > 0 and sl > 0 and tp > 0 and side in ("BUY", "SELL"):
            trade = {"side": side, "entry": entry, "sl": sl, "tp": tp}

    return {
        "ok": True,
        "world": "SCALPING",
        "symbol": symbol,
        "tf": tf,
        "ts_ms": _now_ms(),
        "candles": candles,
        "meta": meta or {},
        "state": state,
        "side": side,
        "price": float(price),
        "zone": (float(zone[0]), float(zone[1])),
        "note": note,
        "score": int(score),
        "light": light,
        "plan": plan,
        "signal": signal,
        "fib": fib or {},
        "params": params,

        # 👇 ROOT fields para Bitácora
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "trade": trade,

        "analysis": {
            "state": state,
            "side": side,
            "zone": {"lo": float(zone[0]), "hi": float(zone[1])},
            "plan_frozen": bool(plan is not None),
            "signal_frozen": bool(signal is not None),
        },
        "ui": {
            "rows": [
                {"k": "Estado", "v": state},
                {"k": "Lado", "v": side},
                {"k": "Precio", "v": float(price)},
                {"k": "Zona", "v": f"{float(zone[0]):.2f} - {float(zone[1]):.2f}"},
                {"k": "Nota", "v": note},
                {"k": "Score", "v": int(score)},
            ]
        },
        "last_error": None,
    }