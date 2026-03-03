# src/atlas/core/xauusd_knowledge.py
"""
ATLAS — XAUUSD (XAUUSDz) — MÓDULO QUIRÚRGICO (PEGAR TAL CUAL)

Qué hace este archivo en ATLAS:
- Le da a ATLAS conocimiento empírico del oro + reglas duras.
- Construye PLANES (NO ejecuta) para:
  A) Continuidad desde zona óptima 0.786 (y 100 como zona riesgosa).
  B) GAP como deuda potencial: NO es gatillo, es TP principal solo si se cumple el ritual.

Mandamientos (duro):
- “Deuda pagada” ≠ reacción. Solo pagada por aceptación (toque+cierres+retest+continuidad) o cambio de estado.
- 0.786 es zona óptima de decisión.
- 100 (1.0) es zona con alta incidencia de stop-hunt/transición: exigir timing estricto.
- GAP: exageración → fallo → ruptura → recuperación. Si falla uno: NO_TRADE.

Backtest (REAL) usado para PRIORS:
- XAUUSDz M5, 2024-09-12 05:10 → 2026-02-11 14:05 (99,964 velas)
- Pivots fractales depth=6 (~30 min), swings n=8,411
- GAPs detectados en M5: umbral 0.15% (open vs prev close), eventos n=58
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple


# =============================================================================
# 1) PRIORS EMPÍRICOS (XAUUSD) — estadística base, NO señal
# =============================================================================

XAU_PRIORS: Dict[str, Any] = {
    "dataset": "XAUUSDz_M5_20240912_20260211",
    "n_swings": 8411,

    # Profundidad de retroceso (overshoot ratio respecto al impulso AB)
    "prob_hit_0618": 0.7737486625,
    "prob_hit_0786": 0.6384496493,
    "prob_hit_100": 0.4848412793,
    "prob_only_0786_without_100": 0.1536083700,

    # Stop-hunt / overshoot
    "prob_overshoot_gt_100": 0.4843657116,
    "prob_ge_1272": 0.3444299132,
    "prob_ge_1618": 0.2243490667,
    "prob_ge_200": 0.1470693140,

    # Retroceso típico
    "retracement_median": 0.9775695029,

    # Impulso típico en M5 (por swing)
    "impulse_minutes_median": 50.0,
    "impulse_points_median": 10.021,

    # “Paga” (continuación rompe el extremo del impulso) por bucket
    "continuation_if_between_0786_and_lt_100": 0.5386996904,
    "continuation_if_ge_100": 0.3619421285,
    "continuation_if_lt_0786": 0.6215060835,

    # TP1 “rápido” orientativo (desde entrada 0.786 hasta el extremo del impulso, SOLO continuaciones)
    # (En XAU “points” = unidades de precio. Convertís a pips/lote en tu módulo de lotaje.)
    "tp1_points_avg_from_0786_in_continuations": 7.4773638370,
    "tp1_points_median_from_0786_in_continuations": 5.4226140000,
}


# =============================================================================
# 2) GAP STATS (XAUUSD) — detección sobre M5 por salto Open vs Close prev
# =============================================================================

XAU_GAP_STATS: Dict[str, Any] = {
    "dataset": "XAUUSDz_M5_20240912_20260211",
    "gap_threshold_pct": 0.0015,  # 0.15%
    "n_gaps": 58,

    # ¿Cuántos gaps vuelven al cierre previo dentro de 6h (72 velas M5)?
    "close_rate_within_6h": 0.6551724138,
    "median_minutes_to_close_within_6h": 20.0,

    # Distribución de gap size
    "median_gap_pct": 0.0025914164,
    "mean_gap_pct": 0.0038176073,

    # Proxy de “aceptación/expansión” inmediata post-gap (primeros 30m se aleja sin tocar nivel)
    "share_acceptance_like_first_30m": 0.4482758621,

    # Por dirección
    "n_up": 39,
    "close_rate_up_within_6h": 0.6666666667,
    "median_minutes_to_close_up_within_6h": 17.5,

    "n_down": 19,
    "close_rate_down_within_6h": 0.6315789474,
    "median_minutes_to_close_down_within_6h": 87.5,
}


# =============================================================================
# 3) REGLAS DURAS (operativa XAUUSD)
# =============================================================================

XAU_RULES: Dict[str, Any] = {
    "symbol_hint": "XAUUSDz / XAUUSD",
    "tf_context": ("H1", "M5"),
    "tf_exec": ("M1", "M3", "M5"),

    # Zonas fibo relevantes
    "poi_0618": 0.618,
    "poi_primary": 0.786,   # zona óptima
    "poi_risky": 1.0,       # 100 (stop-hunt/transición frecuente)
    "stop_hunt_levels": (1.272, 1.618, 2.0),

    # Buffer: por defecto fijo (si tenés ATR, reemplazalo en tu motor)
    "zone_buffer_points_default": 1.50,

    # Gestión orientativa (NO ejecución)
    "tp1_points_band_default": (6.0, 12.0),
    "be_after_tp1": True,

    # GAP
    "gap_close_lookahead_bars_m5": 72,  # 6h
    "gap_threshold_pct": XAU_GAP_STATS["gap_threshold_pct"],

    "allow_no_trade": True,
}


# =============================================================================
# 4) Dataclasses: Planes
# =============================================================================

@dataclass
class XAUPlan:
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


@dataclass
class XAUGapPlan:
    bias: str
    mode: str
    gap_level: float
    entry_style: str
    entry: Optional[float]
    sl: Optional[float]
    tp_gap: Optional[float]
    strictness: str
    reasons: List[str]


# =============================================================================
# 5) Utilidades
# =============================================================================

def fibo_price(A: float, B: float, ratio: float, direction: str) -> float:
    if direction == "down":
        return B + ratio * (A - B)
    return B - ratio * (B - A)

def make_zone(price: float, buffer_points: float) -> Tuple[float, float]:
    return (price - buffer_points, price + buffer_points)

def classify_overshoot_zone(overshoot: float) -> str:
    if overshoot < XAU_RULES["poi_primary"]:
        return "lt_0786"
    if overshoot < XAU_RULES["poi_risky"]:
        return "between_0786_and_lt_100"
    return "ge_100"

def timing_strictness(overshoot: float) -> str:
    return "strict" if overshoot >= XAU_RULES["poi_risky"] else "normal"

def _last_n(candles: List[Dict[str, float]], n: int) -> List[Dict[str, float]]:
    return candles[-n:] if len(candles) >= n else candles[:]


# =============================================================================
# 6) “Deuda pagada” = aceptación (no reacción)
# =============================================================================

def debt_paid_by_acceptance(
    candles: List[Dict[str, float]],
    level: float,
    direction: str,
    lookahead: int = 40,
    buffer: float = 1.0,
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
# 7) Timing: SOLO 3 gatillos permitidos
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


# =============================================================================
# 8) Motor de plan (CONTINUIDAD) — POI principal 0.786
# =============================================================================

def xau_pick_plan(
    bias: str,
    impulse_A: float,
    impulse_B: float,
    overshoot: float,
    exec_candles: List[Dict[str, float]],
    buffer_points: Optional[float] = None,
    tp1_band: Optional[Tuple[float, float]] = None,
) -> XAUPlan:
    reasons: List[str] = []
    buffer_points = float(buffer_points if buffer_points is not None else XAU_RULES["zone_buffer_points_default"])
    tp1_band = tp1_band if tp1_band is not None else XAU_RULES["tp1_points_band_default"]

    direction = "down" if bias == "sell" else "up"
    poi_0786 = fibo_price(impulse_A, impulse_B, XAU_RULES["poi_primary"], direction)
    zone_low, zone_high = make_zone(poi_0786, buffer_points)

    zone_class = classify_overshoot_zone(overshoot)
    strictness = timing_strictness(overshoot)

    if zone_class == "lt_0786":
        return XAUPlan(
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
        reasons.append("Corrección alcanzó/superó 100: stop-hunt o transición probable → timing estricto.")
    else:
        reasons.append("Corrección en zona óptima (0.786–<100): mejor prob. de continuidad.")

    t1 = trigger_direct_touch_close(exec_candles, zone_low, zone_high, bias)
    t2 = trigger_sweep_reclaim(exec_candles, zone_low, zone_high, bias)
    t3 = trigger_break_retest(exec_candles, bias)

    entry_style = "none"
    if t2:
        entry_style = "sweep_reclaim"
        reasons.append("Gatillo: barrida + recuperación (preferido en XAU).")
    elif t1:
        entry_style = "direct_touch"
        reasons.append("Gatillo: toque + cierre válido.")
    elif t3 and strictness == "strict":
        entry_style = "break_retest"
        reasons.append("Gatillo: ruptura + retest (modo estricto por 100+).")
    else:
        return XAUPlan(
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
        f"Zona: 0.786 con buffer {buffer_points:.2f}.",
        f"Strictness: {strictness}.",
        "Gestión XAU: TP1 temprano + BE rápido. Si no paga, salir.",
        "Deuda pagada = aceptación, no reacción.",
    ]

    return XAUPlan(
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


# =============================================================================
# 9) GAP (XAU) — el gap NO es gatillo, es TP si hay ritual completo
# =============================================================================

def detect_gap_event(prev_close: float, current_open: float, threshold_pct: float = XAU_RULES["gap_threshold_pct"]) -> Optional[Dict[str, Any]]:
    if prev_close == 0:
        return None
    gap_points = current_open - prev_close
    gap_pct = abs(gap_points) / abs(prev_close)
    if gap_pct < threshold_pct:
        return None
    return {
        "gap_level": float(prev_close),
        "gap_points": float(gap_points),
        "gap_pct": float(gap_pct),
        "direction": "up" if gap_points > 0 else "down",
    }

def gap_ritual_ok(exec_candles: List[Dict[str, float]], gap_level: float, gap_direction: str) -> bool:
    """
    Ritual GAP (proxy robusto):
    - NO debe tocar gap_level “de casualidad” (si toca sin ritual, no es setup)
    - Debe existir una “exageración” (rango grande relativo) en la ventana reciente
    - Debe existir ruptura + retest en dirección de cierre del gap (modo estricto)
    """
    if len(exec_candles) < 20:
        return False

    last = exec_candles[-20:]

    # Si ya tocó el gap_level sin ritual, NO vale como setup
    touched = any(c["l"] <= gap_level <= c["h"] for c in last)
    if touched:
        return False

    # Exageración proxy: una vela con rango > 2.2x el rango promedio de la ventana
    ranges = [(c["h"] - c["l"]) for c in last]
    if not ranges:
        return False
    avg_r = sum(ranges) / len(ranges)
    big = max(ranges) > avg_r * 2.2
    if not big:
        return False

    # Ruptura + retest (estricto)
    # gap up → buscamos estructura para bajar (sell)
    # gap down → buscamos estructura para subir (buy)
    bias = "sell" if gap_direction == "up" else "buy"
    return trigger_break_retest(exec_candles, bias=bias, internal_lookback=12)

def xau_gap_pick_plan(gap_event: Dict[str, Any], exec_candles: List[Dict[str, float]], buffer_points: Optional[float] = None) -> XAUGapPlan:
    buffer_points = float(buffer_points if buffer_points is not None else XAU_RULES["zone_buffer_points_default"])
    gap_level = float(gap_event["gap_level"])
    gap_dir = str(gap_event["direction"])

    if not gap_ritual_ok(exec_candles, gap_level=gap_level, gap_direction=gap_dir):
        return XAUGapPlan(
            bias="gap_short" if gap_dir == "up" else "gap_long",
            mode="no_trade",
            gap_level=round(gap_level, 3),
            entry_style="none",
            entry=None, sl=None, tp_gap=None,
            strictness="strict",
            reasons=[
                "GAP detectado, pero NO cumple ritual obligatorio.",
                "Gap NO es gatillo: solo es TP si falla la continuidad con evidencia.",
                "Si hay aceptación/expansión, el gap se descarta como objetivo y puede ser combustible.",
            ],
        )

    entry = float(exec_candles[-1]["c"])

    if gap_dir == "up":
        bias = "gap_short"
        recent_high = max(c["h"] for c in _last_n(exec_candles, 8))
        sl = recent_high + buffer_points
    else:
        bias = "gap_long"
        recent_low = min(c["l"] for c in _last_n(exec_candles, 8))
        sl = recent_low - buffer_points

    return XAUGapPlan(
        bias=bias,
        mode="gap_trade",
        gap_level=round(gap_level, 3),
        entry_style="fail_break_retest",
        entry=round(entry, 3),
        sl=round(sl, 3),
        tp_gap=round(gap_level, 3),
        strictness="strict",
        reasons=[
            "Ritual GAP OK: exageración → fallo → ruptura → recuperación (proxy).",
            "Entrada solo en aceptación; SL técnico corto (estructural).",
            "TP principal = cierre del gap (gap_level).",
            "Si el precio acepta/expande contra el cierre, NO insistir.",
        ],
    )


# =============================================================================
# 10) Serialización para snapshot/UI/logs
# =============================================================================

def plan_to_dict(p: XAUPlan) -> Dict[str, Any]:
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

def gap_plan_to_dict(p: XAUGapPlan) -> Dict[str, Any]:
    return {
        "bias": p.bias,
        "mode": p.mode,
        "gap_level": p.gap_level,
        "entry_style": p.entry_style,
        "entry": p.entry,
        "sl": p.sl,
        "tp_gap": p.tp_gap,
        "strictness": p.strictness,
        "reasons": p.reasons,
    }
