from __future__ import annotations
from typing import Dict, Any, List, Tuple

from atlas.core.atlas_types import Decision, POI
from atlas.core.fibo_utils import fibo_0_786_zone, touched_zone_last, closes_outside_zone_against
from atlas.core.lotage import calc_lot_1pct

# ──────────────────────────────────────────────────────────────────────────────
# ALERT FORMAT (EXACTO)
# ──────────────────────────────────────────────────────────────────────────────

def format_alert(poi: POI) -> str:
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

# ──────────────────────────────────────────────────────────────────────────────
# CONTEXTO (simple laboratorio)
# ──────────────────────────────────────────────────────────────────────────────

def _trend_hint(candles: List[Dict[str, float]]) -> str:
    if len(candles) < 30:
        return "UP"
    a = float(candles[-30]["close"])
    b = float(candles[-1]["close"])
    return "UP" if b >= a else "DOWN"

def _two_closes_in_favor(candles: List[Dict[str, float]], side: str) -> bool:
    if len(candles) < 3:
        return False
    c1 = float(candles[-1]["close"])
    c2 = float(candles[-2]["close"])
    return (c1 >= c2) if side == "BUY" else (c1 <= c2)

# ──────────────────────────────────────────────────────────────────────────────
# GATILLOS (SOLO 3)
# ──────────────────────────────────────────────────────────────────────────────

def _trigger_touch_0786(candles: List[Dict[str, float]], zone: List[float], side: str) -> bool:
    last = candles[-1]
    z_low, z_high = float(zone[0]), float(zone[1])
    touched = (float(last["low"]) <= z_high and float(last["high"]) >= z_low)
    if not touched:
        return False
    # vela de decisión simple (laboratorio)
    return (float(last["close"]) > float(last["open"])) if side == "BUY" else (float(last["close"]) < float(last["open"]))

def _trigger_sweep_recover(candles: List[Dict[str, float]], side: str) -> bool:
    if len(candles) < 6:
        return False
    curr = candles[-1]
    prev = candles[-2]
    if side == "BUY":
        recent_low = min(float(c["low"]) for c in candles[-6:-1])
        swept = float(prev["low"]) < recent_low
        recovered = float(curr["close"]) > recent_low
        accepted = float(curr["close"]) > float(curr["open"])
        return bool(swept and recovered and accepted)
    else:
        recent_high = max(float(c["high"]) for c in candles[-6:-1])
        swept = float(prev["high"]) > recent_high
        recovered = float(curr["close"]) < recent_high
        accepted = float(curr["close"]) < float(curr["open"])
        return bool(swept and recovered and accepted)

def _trigger_break_retest_secondary(candles: List[Dict[str, float]], side: str) -> bool:
    if len(candles) < 14:
        return False
    base = candles[-14:-2]
    lvl = max(float(c["high"]) for c in base) if side == "BUY" else min(float(c["low"]) for c in base)
    br = candles[-2]
    rt = candles[-1]

    if side == "BUY":
        broke = float(br["close"]) > lvl
        retest = float(rt["low"]) <= lvl
        accept = float(rt["close"]) > float(rt["open"])
        return bool(broke and retest and accept)
    else:
        broke = float(br["close"]) < lvl
        retest = float(rt["high"]) >= lvl
        accept = float(rt["close"]) < float(rt["open"])
        return bool(broke and retest and accept)

# ──────────────────────────────────────────────────────────────────────────────
# GAP RITUAL (5 pasos)
# ──────────────────────────────────────────────────────────────────────────────

def _gap_ritual(candles: List[Dict[str, float]]) -> Tuple[bool, Dict[str, bool], str]:
    steps = {
        "exageracion": False,
        "fallo_continuidad": False,
        "ruptura": False,
        "recuperacion": False,
        "aceptacion": False
    }
    if len(candles) < 80:
        return False, steps, "GAP_NEEDS_MORE_DATA"

    recent = candles[-40:]
    ranges = [(float(c["high"]) - float(c["low"])) for c in recent]
    avg_r = sum(ranges) / max(1, len(ranges))

    spike_i = -1
    for i in range(len(recent) - 10):
        if ranges[i] > avg_r * 2.2:
            spike_i = i
            break
    if spike_i == -1:
        return False, steps, "GAP_NO_EXAGGERATION"
    steps["exageracion"] = True

    spike = recent[spike_i]
    spike_up = float(spike["close"]) > float(spike["open"])
    after = recent[spike_i + 1: spike_i + 6]
    if len(after) < 4:
        return False, steps, "GAP_WAIT_AFTER_EXAGGERATION"

    # fallo continuidad
    if spike_up:
        if max(float(c["high"]) for c in after[:3]) > float(spike["high"]):
            return False, steps, "GAP_CONTINUITY_OK_NO_TRADE"
    else:
        if min(float(c["low"]) for c in after[:3]) < float(spike["low"]):
            return False, steps, "GAP_CONTINUITY_OK_NO_TRADE"
    steps["fallo_continuidad"] = True

    chunk = candles[-20:]
    internal = chunk[:-2]
    lvl = min(float(c["low"]) for c in internal) if spike_up else max(float(c["high"]) for c in internal)
    br = chunk[-2]
    if spike_up:
        if not (float(br["close"]) < lvl):
            return False, steps, "GAP_WAIT_RUPTURE"
    else:
        if not (float(br["close"]) > lvl):
            return False, steps, "GAP_WAIT_RUPTURE"
    steps["ruptura"] = True

    rt = chunk[-1]
    if spike_up:
        if not (float(rt["high"]) >= lvl):
            return False, steps, "GAP_WAIT_RECOVERY"
    else:
        if not (float(rt["low"]) <= lvl):
            return False, steps, "GAP_WAIT_RECOVERY"
    steps["recuperacion"] = True

    if spike_up:
        if not (float(rt["close"]) < float(rt["open"])):
            return False, steps, "GAP_WAIT_ACCEPTANCE"
    else:
        if not (float(rt["close"]) > float(rt["open"])):
            return False, steps, "GAP_WAIT_ACCEPTANCE"
    steps["aceptacion"] = True

    return True, steps, "GAP_RITUAL_OK"

# ──────────────────────────────────────────────────────────────────────────────
# EVALUATE
# ──────────────────────────────────────────────────────────────────────────────

def evaluate(world: str, symbol: str, tf: str, candles: List[Dict[str, float]]) -> Decision:
    w = (world or "GENERAL").strip().upper()
    s = (symbol or "XAUUSD").strip().upper()
    t = (tf or "M1").strip().upper()

    checklist: Dict[str, bool] = {"contexto": False, "zona": False, "timing": False, "fibo_0.786": False}
    fibo: Dict[str, Any] = {"level": 0.786, "valid": False, "zone": None, "swing": None}

    if not candles or len(candles) < 60:
        return Decision(False, "NO_TRADE", "NO_CANDLES", checklist, fibo, None)

    # GAP primero
    if w == "GAP":
        ok, steps, reason = _gap_ritual(candles)
        for k, v in steps.items():
            checklist[k] = bool(v)
        if not ok:
            return Decision(False, "WAIT", reason, checklist, fibo, None)

        checklist["contexto"] = True
        checklist["zona"] = True
        checklist["timing"] = True

        last = candles[-1]
        side = "SELL" if float(last["close"]) < float(last["open"]) else "BUY"
        entry = float(last["close"])
        chunk = candles[-10:]
        sl = max(float(c["high"]) for c in chunk) if side == "SELL" else min(float(c["low"]) for c in chunk)
        if abs(entry - sl) <= 0:
            return Decision(False, "NO_TRADE", "BAD_RISK_GEOMETRY", checklist, fibo, None)

        risk = abs(entry - sl)
        parcial = entry - risk * 2.0 if side == "SELL" else entry + risk * 2.0
        tp2 = entry - risk * 4.0 if side == "SELL" else entry + risk * 4.0
        rr_tp2 = round(abs(tp2 - entry) / risk, 2)

        lot, lot_note = calc_lot_1pct(s, entry, sl, balance=10000.0, risk_pct=0.01)

        poi = POI(
            symbol=s, side=side, trigger="GAP: Ritual completo",
            entry=round(entry, 2), sl=round(sl, 2),
            parcial=round(parcial, 2), tp2=round(tp2, 2),
            rr_tp2=rr_tp2, lot_sim=float(lot),
            tf=t, world=w, note=lot_note
        )
        return Decision(True, "CONFIRMED", "CONFIRMED", checklist, fibo, poi)

    # GENERAL / PRESESION / GATILLOS / ATLAS_IA
    trend = _trend_hint(candles)
    side = "BUY" if trend == "UP" else "SELL"
    checklist["contexto"] = True

    allow_079 = (w == "PRESESION")
    if allow_079:
        checklist["fibo_0.79_only_here"] = True  # marca para UI, sin contaminar otros mundos

    z = fibo_0_786_zone(
        candles,
        direction=("UP" if side == "BUY" else "DOWN"),
        allow_079=allow_079
    )
    if not z.get("ok"):
        return Decision(False, "NO_TRADE", f"FIBO_FAIL_{z.get('reason')}", checklist, fibo, None)

    fibo["zone"] = z["zone"]
    fibo["swing"] = z["swing"]
    fibo["valid"] = True
    checklist["fibo_0.786"] = True

    if not touched_zone_last(candles, z["zone"], last_n=12):
        return Decision(False, "WAIT", "WAIT_TOUCH_0_786", checklist, fibo, None)
    checklist["zona"] = True

    if closes_outside_zone_against(candles, z["zone"], side=side):
        return Decision(False, "NO_TRADE", "INVALIDATED_BY_TWO_CLOSES", checklist, fibo, None)

    timing_ok = _two_closes_in_favor(candles, side=side)

    trig1 = _trigger_touch_0786(candles, z["zone"], side)
    trig2 = _trigger_sweep_recover(candles, side)
    trig3 = _trigger_break_retest_secondary(candles, side)

    trigger = None
    if trig2:
        trigger = "Barrida + recuperación"
    elif trig3:
        trigger = "Ruptura + retest secundario"
    elif trig1:
        trigger = "Toque 0.786 confirmado"

    if w == "GATILLOS" and not trigger:
        return Decision(False, "WAIT", "WAIT_TRIGGER", checklist, fibo, None)

    if not timing_ok:
        return Decision(False, "WAIT", "WAIT_TIMING_CONFIRM", checklist, fibo, None)

    if not trigger:
        trigger = "Pullback y rechazo"

    checklist["timing"] = True

    last = candles[-1]
    entry = float(last["close"])
    chunk = candles[-8:]
    sl = min(float(c["low"]) for c in chunk) if side == "BUY" else max(float(c["high"]) for c in chunk)
    if abs(entry - sl) <= 0:
        return Decision(False, "NO_TRADE", "BAD_RISK_GEOMETRY", checklist, fibo, None)

    risk = abs(entry - sl)
    parcial = entry + risk * 1.8 if side == "BUY" else entry - risk * 1.8
    tp2 = entry + risk * 3.2 if side == "BUY" else entry - risk * 3.2
    rr_tp2 = round(abs(tp2 - entry) / risk, 2)

    lot, lot_note = calc_lot_1pct(s, entry, sl, balance=10000.0, risk_pct=0.01)

    poi = POI(
        symbol=s, side=side, trigger=trigger,
        entry=round(entry, 5), sl=round(sl, 5),
        parcial=round(parcial, 5), tp2=round(tp2, 5),
        rr_tp2=rr_tp2, lot_sim=float(lot),
        tf=t, world=w, note=lot_note
    )
    return Decision(True, "CONFIRMED", "CONFIRMED", checklist, fibo, poi)
