from __future__ import annotations
from typing import Dict, Any, List
from atlas.core.atlas_types import Decision, POI
from atlas.core.fibo_utils import fibo_0_786_zone, touched_zone_last
from atlas.core.lotage import calc_lot_1pct

def _trend_hint(candles: List[Dict[str, float]]) -> str:
    if len(candles) < 20:
        return "UP"
    a = candles[-20]["close"]
    b = candles[-1]["close"]
    return "UP" if b >= a else "DOWN"

def evaluate(world: str, symbol: str, tf: str, candles: List[Dict[str, float]]) -> Decision:
    w = (world or "GENERAL").strip().upper()
    s = (symbol or "XAUUSD").strip().upper()
    t = (tf or "M1").strip().upper()

    checklist = {"contexto": False, "zona": False, "timing": False, "fibo": False}
    fibo = {"level": 0.786, "valid": False, "zone": None, "swing": None}

    if not candles or len(candles) < 50:
        return Decision(False, "NO_TRADE", "NO_CANDLES", checklist, fibo, None)

    # GAP: por ahora NO confirma (ritual completo viene en motor real)
    if w == "GAP":
        return Decision(False, "WAIT", "GAP_NEEDS_RITUAL", checklist, fibo, None)

    trend = _trend_hint(candles)
    side = "BUY" if trend == "UP" else "SELL"

    # FIBO obligatorio 0.786-0.79
    z = fibo_0_786_zone(candles, direction=("UP" if side == "BUY" else "DOWN"))
    if not z.get("ok"):
        return Decision(False, "NO_TRADE", f"FIBO_FAIL_{z.get('reason')}", checklist, fibo, None)

    fibo["zone"] = z["zone"]
    fibo["swing"] = z["swing"]

    if not touched_zone_last(candles, z["zone"], last_n=10):
        return Decision(False, "WAIT", "WAIT_TOUCH_0_786", checklist, {**fibo, "valid": False}, None)

    # Timing mínimo (laboratorio): cierre a favor (no es el motor final)
    last = candles[-1]
    prev = candles[-2]
    if side == "BUY":
        timing_ok = (last["close"] >= prev["close"])
    else:
        timing_ok = (last["close"] <= prev["close"])

    checklist["contexto"] = True
    checklist["zona"] = True
    checklist["timing"] = bool(timing_ok)
    checklist["fibo"] = True
    fibo["valid"] = True

    if not timing_ok:
        return Decision(False, "WAIT", "WAIT_TIMING_CONFIRM", checklist, fibo, None)

    entry = float(last["close"])
    chunk = candles[-6:]
    lo = min(c["low"] for c in chunk)
    hi = max(c["high"] for c in chunk)

    trigger = "Pullback y rechazo"

    if side == "BUY":
        sl = float(lo)
        risk = entry - sl
        parcial = entry + risk * 1.8
        tp2 = entry + risk * 3.2
    else:
        sl = float(hi)
        risk = sl - entry
        parcial = entry - risk * 1.8
        tp2 = entry - risk * 3.2

    if risk <= 0:
        return Decision(False, "NO_TRADE", "BAD_RISK_GEOMETRY", checklist, fibo, None)

    rr_tp2 = abs(tp2 - entry) / risk
    lot, lot_note = calc_lot_1pct(s, entry, sl, balance=10000.0, risk_pct=0.01)

    poi = POI(
        symbol=s,
        side=side,
        trigger=trigger,
        entry=round(entry, 5),
        sl=round(sl, 5),
        parcial=round(parcial, 5),
        tp2=round(tp2, 5),
        rr_tp2=round(rr_tp2, 2),
        lot_sim=float(lot),
        tf=t,
        world=w,
        note=lot_note,
    )

    return Decision(True, "CONFIRMED", "CONFIRMED_BASELINE", checklist, fibo, poi)

def format_alert(poi: POI) -> str:
    # FORMATO EXACTO pedido (sin frases extra)
    lines = [
        f"{poi.symbol}",
        f"{poi.trigger}",
        "",
        f"{poi.side} {poi.entry}",
        f"SL {poi.sl}",
        f"PARCIAL {poi.parcial}",
        f"TP2 {poi.tp2}",
    ]
    return "\n".join(lines)