# src/atlas/core/usoil_knowledge.py
"""
ATLAS — USOIL (USOILz) — KNOWLEDGE MODULE QUIRÚRGICO (PEGAR TAL CUAL)

Qué hace este archivo en ATLAS:
- Backtestea cómo retrocede/barre USOIL (M5) y lo convierte en PRIORS.
- Devuelve un PLAN (zona 0.786 + timing) o NO_TRADE.
- NO ejecuta trades.

Dataset usado (REAL):
- USOILz M5: 2024-09-03 19:15 → 2026-02-11 14:45 (99,964 velas)
- Pivots fractales depth=6 → swings n=8,542
- Filtro anti-ruido (25% inferior por tamaño):
  min_impulse_pts_filter = 0.193
  swings filtrados n=6,406

Mandamientos:
- 0.786 = zona óptima (NO señal).
- 100 = zona riesgosa (barrida/transición) → timing estricto.
- “Deuda pagada” solo por aceptación o cambio de estado.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple


USOIL_PRIORS: Dict[str, Any] = {
    "dataset": "USOILz_M5_20240903_20260211",
    "n_swings_raw": 8542,
    "min_impulse_pts_filter": 0.193,
    "n_swings_filtered": 6406,

    "prob_hit_0618": 0.7069934436,
    "prob_hit_0786": 0.5729004059,
    "prob_hit_100": 0.4186699969,
    "prob_only_0786_without_100": 0.1542304090,

    "prob_overshoot_gt_100": 0.4158601311,
    "prob_ge_1272": 0.2926943490,
    "prob_ge_1618": 0.1793630971,
    "prob_ge_200": 0.1084920387,

    "retracement_median": 0.8757279175,

    "impulse_minutes_median": 55.0,
    "impulse_points_median": 0.4120,

    "continuation_if_between_0786_and_lt_100": 0.4898785425,
    "continuation_if_ge_100": 0.3072334079,
    "continuation_if_lt_0786": 0.6023391813,

    "tp1_points_avg_from_0786_in_continuations": 0.2923126789,
    "tp1_points_median_from_0786_in_continuations": 0.2499480000,
}


USOIL_RULES: Dict[str, Any] = {
    "symbol_hint": "USOILz / USOIL",
    "tf_context": ("H4", "H1", "M15", "M5"),
    "tf_exec": ("M1", "M3", "M5"),

    "poi_0618": 0.618,
    "poi_primary": 0.786,
    "poi_risky": 1.0,
    "stop_hunt_levels": (1.272, 1.618, 2.0),

    # USOIL buffer default (price units). 0.08 ~ 8 centavos
    "zone_buffer_points_default": 0.08,

    # TP1 banda orientativa (0.25–0.55 aprox) según stats y volatilidad típica
    "tp1_points_band_default": (0.25, 0.55),
    "be_after_tp1": True,

    "allow_no_trade": True,
}


@dataclass
class USOILPlan:
    bias: str
    mode: str
    zone_low: float
    zone_high: float
    entry_style: str
    entry: Optional[float]
    sl: Optional[float]
    tp1: Optional[float]
    tp2: Optional[float]
    strictness: str
    reasons: List[str]


def fibo_price(A: float, B: float, ratio: float, direction: str) -> float:
    if direction == "down":
        return B + ratio * (A - B)
    return B - ratio * (B - A)

def make_zone(price: float, buffer_points: float) -> Tuple[float, float]:
    return (price - buffer_points, price + buffer_points)

def classify_overshoot_zone(overshoot: float) -> str:
    if overshoot < USOIL_RULES["poi_primary"]:
        return "lt_0786"
    if overshoot < USOIL_RULES["poi_risky"]:
        return "between_0786_and_lt_100"
    return "ge_100"

def timing_strictness(overshoot: float) -> str:
    return "strict" if overshoot >= USOIL_RULES["poi_risky"] else "normal"

def _last_n(candles: List[Dict[str, float]], n: int) -> List[Dict[str, float]]:
    return candles[-n:] if len(candles) >= n else candles[:]


def debt_paid_by_acceptance(
    candles: List[Dict[str, float]],
    level: float,
    direction: str,
    lookahead: int = 40,
    buffer: float = 0.12,  # buffer aceite (12 centavos)
) -> bool:
    if not candles:
        return False

    touched = False
    closes: List[float] = []
    hh = float("-inf")
    ll = float("inf")

    for i in range(min(len(candles), lookahead)):
        h = float(candles[i]["h"])
        l = float(candles[i]["l"])
        c = float(candles[i]["c"])
        hh = max(hh, h)
        ll = min(ll, l)
        if l <= level <= h:
            touched = True
        if touched:
            closes.append(c)

    if not touched or len(closes) < 5:
        return False

    if direction == "down":
        ok2 = (closes[0] < level and closes[1] < level) or (closes[1] < level and closes[2] < level)
        return ok2 and (ll < (level - buffer))
    else:
        ok2 = (closes[0] > level and closes[1] > level) or (closes[1] > level and closes[2] > level)
        return ok2 and (hh > (level + buffer))


def trigger_direct_touch_close(candles: List[Dict[str, float]], zone_low: float, zone_high: float, bias: str) -> bool:
    if len(candles) < 1:
        return False
    last = candles[-1]
    touched = (last["l"] <= zone_high and last["h"] >= zone_low)
    if not touched:
        return False
    return (last["c"] < zone_low) if bias == "sell" else (last["c"] > zone_high)

def trigger_sweep_reclaim(candles: List[Dict[str, float]], zone_low: float, zone_high: float, bias: str) -> bool:
    if len(candles) < 2:
        return False
    a, b = candles[-2], candles[-1]
    if bias == "sell":
        swept = a["h"] > zone_high or b["h"] > zone_high
        reclaimed = b["c"] < zone_high
        return swept and reclaimed
    swept = a["l"] < zone_low or b["l"] < zone_low
    reclaimed = b["c"] > zone_low
    return swept and reclaimed

def trigger_break_retest(candles: List[Dict[str, float]], bias: str, internal_lookback: int = 12) -> bool:
    if len(candles) < internal_lookback + 3:
        return False

    seg = candles[-(internal_lookback + 3):]
    prev = seg[:-3]
    x = seg[-3]
    y = seg[-2]
    z = seg[-1]

    prev_low = min(c["l"] for c in prev)
    prev_high = max(c["h"] for c in prev)

    if bias == "sell":
        broke = x["l"] < prev_low
        retest_fail = y["h"] <= prev_low and z["c"] <= prev_low
        return broke and retest_fail
    broke = x["h"] > prev_high
    retest_hold = y["l"] >= prev_high and z["c"] >= prev_high
    return broke and retest_hold


def usoil_pick_plan(
    bias: str,
    impulse_A: float,
    impulse_B: float,
    overshoot: float,
    exec_candles: List[Dict[str, float]],
    buffer_points: Optional[float] = None,
    tp1_band: Optional[Tuple[float, float]] = None,
) -> USOILPlan:
    reasons: List[str] = []
    buffer_points = float(buffer_points if buffer_points is not None else USOIL_RULES["zone_buffer_points_default"])
    tp1_band = tp1_band if tp1_band is not None else USOIL_RULES["tp1_points_band_default"]

    direction = "down" if bias == "sell" else "up"
    poi_0786 = fibo_price(impulse_A, impulse_B, USOIL_RULES["poi_primary"], direction)
    zone_low, zone_high = make_zone(poi_0786, buffer_points)

    zone_class = classify_overshoot_zone(overshoot)
    strictness = timing_strictness(overshoot)

    if zone_class == "lt_0786":
        return USOILPlan(
            bias=bias,
            mode="no_trade",
            zone_low=round(zone_low, 3),
            zone_high=round(zone_high, 3),
            entry_style="none",
            entry=None, sl=None, tp1=None, tp2=None,
            strictness="normal",
            reasons=[
                "No alcanzó 0.786: tendencia fuerte (NO perseguir).",
                "Esperar siguiente tramo o llegada real a zona de decisión.",
            ],
        )

    if zone_class == "ge_100":
        reasons.append("Corrección alcanzó/superó 100: transición/barrida probable → timing estricto.")
    else:
        reasons.append("Corrección en zona óptima (0.786–<100): mejor prob. de continuidad.")

    t1 = trigger_direct_touch_close(exec_candles, zone_low, zone_high, bias)
    t2 = trigger_sweep_reclaim(exec_candles, zone_low, zone_high, bias)
    t3 = trigger_break_retest(exec_candles, bias)

    entry_style = "none"
    if t2:
        entry_style = "sweep_reclaim"
        reasons.append("Gatillo: barrida + recuperación.")
    elif t1:
        entry_style = "direct_touch"
        reasons.append("Gatillo: toque + cierre válido.")
    elif t3 and strictness == "strict":
        entry_style = "break_retest"
        reasons.append("Gatillo: ruptura + retest (modo estricto por 100+).")
    else:
        return USOILPlan(
            bias=bias,
            mode="no_trade",
            zone_low=round(zone_low, 3),
            zone_high=round(zone_high, 3),
            entry_style="none",
            entry=None, sl=None, tp1=None, tp2=None,
            strictness=strictness,
            reasons=reasons + ["No hubo timing válido. Silencio operativo."],
        )

    entry = float(exec_candles[-1]["c"])
    last6 = _last_n(exec_candles, 6) or exec_candles

    if bias == "sell":
        recent_high = max(c["h"] for c in last6)
        sl = max(zone_high + buffer_points * 0.8, recent_high + buffer_points * 0.3)
        tp1 = entry - float(tp1_band[0])
        tp2 = entry - float(tp1_band[1])
    else:
        recent_low = min(c["l"] for c in last6)
        sl = min(zone_low - buffer_points * 0.8, recent_low - buffer_points * 0.3)
        tp1 = entry + float(tp1_band[0])
        tp2 = entry + float(tp1_band[1])

    mode = "continuation" if zone_class == "between_0786_and_lt_100" else "transition_risk"

    reasons += [
        f"Zona: 0.786 con buffer {buffer_points:.3f}.",
        f"Strictness: {strictness}.",
        "Gestión USOIL: TP1 temprano + BE rápido; si no paga, salir.",
        "Deuda pagada = aceptación, no reacción.",
    ]

    return USOILPlan(
        bias=bias,
        mode=mode,
        zone_low=round(zone_low, 3),
        zone_high=round(zone_high, 3),
        entry_style=entry_style,
        entry=round(entry, 3),
        sl=round(sl, 3),
        tp1=round(tp1, 3),
        tp2=round(tp2, 3),
        strictness=strictness,
        reasons=reasons,
    )


def plan_to_dict(p: USOILPlan) -> Dict[str, Any]:
    return {
        "bias": p.bias,
        "mode": p.mode,
        "zone": {"low": p.zone_low, "high": p.zone_high},
        "entry_style": p.entry_style,
        "entry": p.entry,
        "sl": p.sl,
        "tp1": p.tp1,
        "tp2": p.tp2,
        "strictness": p.strictness,
        "reasons": p.reasons,
    }
