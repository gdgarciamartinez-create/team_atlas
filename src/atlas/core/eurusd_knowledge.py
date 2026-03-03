# src/atlas/core/eurusd_knowledge.py
"""
ATLAS — EURUSD (EURUSDz) — KNOWLEDGE MODULE QUIRÚRGICO (PEGAR TAL CUAL)

Qué hace este archivo en ATLAS (cortito):
- Backtestea “cómo retrocede y cómo barre” EURUSD (en M5) y lo convierte en PRIORS.
- Convierte (sesgo macro → último impulso A→B → overshoot → timing) en un PLAN con:
  zona (0.786), entry/SL/TP1/TP2 y razones.
- NO ejecuta trades. Solo genera planes o NO_TRADE.

Dataset usado (REAL):
- EURUSDz M5: 2024-10-08 01:55 → 2026-02-11 14:45 (99,963 velas)
- Pivots fractales depth=6 → swings n=8,607
- Para evitar ruido (impulsos demasiado chicos), se filtra el 25% inferior por tamaño:
  min_impulse_pts_filter = 0.00084 (≈ 8.4 pips)
  swings filtrados n=6,475

Mandamientos (duro):
- 0.786 es zona óptima de decisión (NO señal).
- 1.0 (100) es zona con más barridas/transición → timing más estricto.
- “Deuda pagada” ≠ reacción: pagada solo por aceptación (toque+cierres+retest+continuidad) o cambio de estado.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple


# =============================================================================
# 1) PRIORS EMPÍRICOS (EURUSD) — estadística base, NO señal
# =============================================================================

EUR_PRIORS: Dict[str, Any] = {
    "dataset": "EURUSDz_M5_20241008_20260211",
    "n_swings_raw": 8607,
    "min_impulse_pts_filter": 0.00084,  # filtro anti-ruido (≈ 8.4 pips)
    "n_swings_filtered": 6475,

    # Profundidad de retroceso (overshoot ratio respecto al impulso AB)
    "prob_hit_0618": 0.7132046332,
    "prob_hit_0786": 0.5672586873,
    "prob_hit_100": 0.4052509653,
    "prob_only_0786_without_100": 0.1620077220,

    # Stop-hunt / overshoot
    "prob_overshoot_gt_100": 0.3986100386,
    "prob_ge_1272": 0.2741312741,
    "prob_ge_1618": 0.1793050193,
    "prob_ge_200": 0.1099613900,

    # Retroceso típico
    "retracement_median": 0.8720000000,

    # Impulso típico en M5
    "impulse_minutes_median": 55.0,
    "impulse_points_median": 0.00167,  # ≈ 16.7 pips

    # Continuidad (rompe el extremo del impulso) por bucket
    "continuation_if_between_0786_and_lt_100": 0.4966634890,
    "continuation_if_ge_100": 0.2782012195,
    "continuation_if_lt_0786": 0.5995717345,

    # TP1 orientativo desde entrada 0.786 → extremo del impulso (solo continuaciones)
    "tp1_points_avg_from_0786_in_continuations": 0.0011904350,  # ≈ 11.9 pips
    "tp1_points_median_from_0786_in_continuations": 0.0010139400,  # ≈ 10.1 pips
}


# =============================================================================
# 2) REGLAS DURAS (EURUSD)
# =============================================================================

EUR_RULES: Dict[str, Any] = {
    "symbol_hint": "EURUSDz / EURUSD",
    "tf_context": ("H4", "H1", "M15", "M5"),
    "tf_exec": ("M1", "M3", "M5"),

    # Fibo
    "poi_0618": 0.618,
    "poi_primary": 0.786,  # zona óptima
    "poi_risky": 1.0,      # 100 (más barridas/transición)
    "stop_hunt_levels": (1.272, 1.618, 2.0),

    # Buffer por defecto (price units). Para EURUSD: 0.00025 ≈ 2.5 pips
    "zone_buffer_points_default": 0.00025,

    # Gestión orientativa (NO ejecución)
    # Banda TP1 (≈ 8–15 pips), alineado a stats.
    "tp1_points_band_default": (0.00080, 0.00150),
    "be_after_tp1": True,

    "allow_no_trade": True,
}


# =============================================================================
# 3) Plan
# =============================================================================

@dataclass
class EURPlan:
    bias: str                    # "sell" o "buy" (macro del sistema)
    mode: str                    # "continuation" / "transition_risk" / "no_trade"
    zone_low: float
    zone_high: float
    entry_style: str             # "direct_touch" / "sweep_reclaim" / "break_retest" / "none"
    entry: Optional[float]
    sl: Optional[float]
    tp1: Optional[float]
    tp2: Optional[float]
    strictness: str              # "normal" / "strict"
    reasons: List[str]


# =============================================================================
# 4) Utilidades
# =============================================================================

def fibo_price(A: float, B: float, ratio: float, direction: str) -> float:
    # direction: "down" (A high -> B low) | "up" (A low -> B high)
    if direction == "down":
        return B + ratio * (A - B)
    return B - ratio * (B - A)

def make_zone(price: float, buffer_points: float) -> Tuple[float, float]:
    return (price - buffer_points, price + buffer_points)

def classify_overshoot_zone(overshoot: float) -> str:
    if overshoot < EUR_RULES["poi_primary"]:
        return "lt_0786"
    if overshoot < EUR_RULES["poi_risky"]:
        return "between_0786_and_lt_100"
    return "ge_100"

def timing_strictness(overshoot: float) -> str:
    return "strict" if overshoot >= EUR_RULES["poi_risky"] else "normal"

def _last_n(candles: List[Dict[str, float]], n: int) -> List[Dict[str, float]]:
    return candles[-n:] if len(candles) >= n else candles[:]


# =============================================================================
# 5) “Deuda pagada” = aceptación (no reacción)
# =============================================================================

def debt_paid_by_acceptance(
    candles: List[Dict[str, float]],
    level: float,
    direction: str,
    lookahead: int = 40,
    buffer: float = 0.00040,  # ≈ 4 pips
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


# =============================================================================
# 6) Timing (3 gatillos)
# =============================================================================

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
    x = seg[-3]  # ruptura
    y = seg[-2]  # retest
    z = seg[-1]  # confirmación

    prev_low = min(c["l"] for c in prev)
    prev_high = max(c["h"] for c in prev)

    if bias == "sell":
        broke = x["l"] < prev_low
        retest_fail = y["h"] <= prev_low and z["c"] <= prev_low
        return broke and retest_fail
    broke = x["h"] > prev_high
    retest_hold = y["l"] >= prev_high and z["c"] >= prev_high
    return broke and retest_hold


# =============================================================================
# 7) Motor de plan (EUR)
# =============================================================================

def eur_pick_plan(
    bias: str,
    impulse_A: float,
    impulse_B: float,
    overshoot: float,
    exec_candles: List[Dict[str, float]],
    buffer_points: Optional[float] = None,
    tp1_band: Optional[Tuple[float, float]] = None,
) -> EURPlan:
    reasons: List[str] = []
    buffer_points = float(buffer_points if buffer_points is not None else EUR_RULES["zone_buffer_points_default"])
    tp1_band = tp1_band if tp1_band is not None else EUR_RULES["tp1_points_band_default"]

    direction = "down" if bias == "sell" else "up"
    poi_0786 = fibo_price(impulse_A, impulse_B, EUR_RULES["poi_primary"], direction)
    zone_low, zone_high = make_zone(poi_0786, buffer_points)

    zone_class = classify_overshoot_zone(overshoot)
    strictness = timing_strictness(overshoot)

    if zone_class == "lt_0786":
        return EURPlan(
            bias=bias,
            mode="no_trade",
            zone_low=zone_low, zone_high=zone_high,
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
        return EURPlan(
            bias=bias,
            mode="no_trade",
            zone_low=zone_low, zone_high=zone_high,
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
        f"Zona: 0.786 con buffer {buffer_points:.5f}.",
        f"Strictness: {strictness}.",
        "Gestión EUR: TP1 temprano + BE rápido; si no paga, salir.",
        "Deuda pagada = aceptación, no reacción.",
    ]

    return EURPlan(
        bias=bias,
        mode=mode,
        zone_low=round(zone_low, 6),
        zone_high=round(zone_high, 6),
        entry_style=entry_style,
        entry=round(entry, 6),
        sl=round(sl, 6),
        tp1=round(tp1, 6),
        tp2=round(tp2, 6),
        strictness=strictness,
        reasons=reasons,
    )


def plan_to_dict(p: EURPlan) -> Dict[str, Any]:
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
