# src/atlas/core/nasdaq_knowledge.py
"""
ATLAS — NASDAQ (USTECz / NAS100) — BLOQUE FINAL QUIRÚRGICO (PEGAR TAL CUAL)

Objetivo:
- Darle a ATLAS una “lectura” operativa del NASDAQ basada en:
  1) Estado macro (sesgo dominante ya lo trae el sistema)
  2) Zonas (Fibo + zonas de interés del último tramo)
  3) Timing (solo 3 gatillos permitidos)
- Convertir backtest en “prioridades” (qué zona paga más, cuándo exigir validación más estricta).
- Evitar “anticipación”: ATLAS no adivina. ATLAS diagnostica y exige evidencia.

Notas doctrinales (duro):
- NAS se mueve rápido: TP1 temprano + BE rápido; si no paga rápido, salir.
- 0.786 es zona óptima de decisión para continuidad / agotamiento.
- 1.0 (100) es zona con alta incidencia de stop-hunt/transición → timing más estricto.
- “Deuda pagada” NO es reacción: es aceptación (toque + cierres + retesteo + continuidad) o cambio de estado.

Integración típica:
- Importar NAS_RULES + funciones `nas_pick_plan(...)` desde tu motor doctrinal / scanner.
- Esto NO ejecuta trades. Devuelve planes, niveles y exigencias de timing.

Entrada esperada:
- Candles: lista dicts con {"t":..., "o":..., "h":..., "l":..., "c":...} (t opcional)
- Sesgo macro: "sell" o "buy" (dominante de tu sistema)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple


# =============================================================================
# 1) PRIOR EMPÍRICO (desde backtest quirúrgico que hicimos para NAS)
#    (ATLAS lo usa como “probabilidades base”, NO como señal)
# =============================================================================

NAS_PRIORS: Dict[str, Any] = {
    # Profundidad de retroceso (overshoot medido como ratio respecto al impulso AB)
    "prob_hit_0786": 0.6315,
    "prob_hit_100": 0.4907,
    "prob_only_0786_without_100": 0.1408,
    "prob_overshoot_gt_100": 0.4803,  # stop-hunt arriba/abajo del 100 es MUY frecuente

    # Extensiones típicas cuando hay stop-hunt (>1.0)
    "prob_ge_1272": 0.3553,
    "prob_ge_1618": 0.2366,
    "prob_ge_200": 0.1601,

    # Retroceso típico
    "retracement_median": 0.964,  # “típico” cerca del 100

    # “Paga” (continuación rompe el extremo del impulso) por zona
    "continuation_if_between_0786_and_lt_100": 0.5194,
    "continuation_if_ge_100": 0.3526,  # baja (más transición / stop-hunt / cambio de estado)
    "continuation_if_lt_0786": 0.6370,  # tendencia fuerte (pero no operable por pullback profundo)

    # Tamaño/tiempo típico del impulso M5
    "impulse_minutes_median": 50.0,
    "impulse_points_median": 57.2,

    # TP1 típico desde entrada 0.786 hacia el extremo del impulso (en continuaciones)
    "tp1_points_band": (30.0, 45.0),
    "tp1_points_avg": 41.46,
    "tp1_points_median": 31.04,
}


# =============================================================================
# 2) REGLAS DURAS (operativa NAS)
# =============================================================================

NAS_RULES: Dict[str, Any] = {
    "symbol_hint": "USTECz / NAS100",
    "tf_context": "M5",      # lectura base
    "tf_exec": ("M1", "M3", "M5"),  # timing
    "poi_primary": 0.786,    # zona óptima
    "poi_risky": 1.0,        # 100 (stop-hunt frecuente)
    "stop_hunt_levels": (1.272, 1.618, 2.0),

    # Buffer de zona: NAS se “pasa” fácil; si lo haces muy fino te lo barre
    # (puedes reemplazar por ATR/volatilidad si ya lo tienes en el sistema)
    "zone_buffer_points": 12.0,  # default conservador para NAS (ajustable)

    # Timing: si llega a 100 o más → exigir modo estricto
    "strict_timing_from_100": True,

    # Gestión: si no paga rápido, salir (NAS no perdona lentitud)
    "tp1_points_band": NAS_PRIORS["tp1_points_band"],
    "be_after_tp1": True,

    # Silencio operativo es válido
    "allow_no_trade": True,
}


# =============================================================================
# 3) DATACLASS: Plan final para que ATLAS lo consuma
# =============================================================================

@dataclass
class NASPlan:
    bias: str                     # "sell" o "buy"
    scenario: str                 # "continuation" / "transition_risk" / "no_trade"
    zone_low: float
    zone_high: float
    entry_style: str              # "direct_touch" / "sweep_reclaim" / "break_retest" / "none"
    entry: Optional[float]
    sl: Optional[float]
    tp1: Optional[float]
    tp2: Optional[float]
    strictness: str               # "normal" / "strict"
    reasons: List[str]


# =============================================================================
# 4) UTILIDADES FIBO (sin dependencia externa)
#    Definimos impulso AB y medimos corrección/overshoot como ratio.
# =============================================================================

def fibo_price(A: float, B: float, ratio: float, direction: str) -> float:
    """
    direction:
      - "down": impulso A (alto) -> B (bajo). Retroceso sube desde B hacia A.
      - "up":   impulso A (bajo) -> B (alto). Retroceso baja desde B hacia A.
    """
    if direction == "down":
        # retroceso = B + ratio*(A-B)
        return B + ratio * (A - B)
    else:
        # retroceso = B - ratio*(B-A)
        return B - ratio * (B - A)

def make_zone(price: float, buffer_points: float) -> Tuple[float, float]:
    return (price - buffer_points, price + buffer_points)

def classify_overshoot_zone(overshoot: float) -> str:
    """
    overshoot:
      - <0.786: no llegó a zona óptima (tendencia fuerte, no perseguir)
      - [0.786,1.0): zona óptima
      - >=1.0: zona stop-hunt/transición (exigir timing estricto)
    """
    if overshoot < NAS_RULES["poi_primary"]:
        return "lt_0786"
    if overshoot < NAS_RULES["poi_risky"]:
        return "between_0786_and_lt_100"
    return "ge_100"

def timing_strictness(overshoot: float) -> str:
    return "strict" if overshoot >= NAS_RULES["poi_risky"] else "normal"


# =============================================================================
# 5) “DEUDA PAGADA” (criterio ATLAS): reacción ≠ pagada
# =============================================================================

def debt_paid_by_acceptance(
    candles: List[Dict[str, float]],
    level: float,
    direction: str,
    lookahead: int = 30
) -> bool:
    """
    Aceptación mínima:
    - Toque del nivel
    - +2 cierres en dirección esperada (confirmación)
    - + retesteo y continuidad (desplazamiento)
    Esto es un filtro conceptual para validar “pagada”.

    direction:
      - "down": queremos confirmar que el nivel actuó como techo (precio por debajo y continúa)
      - "up":   queremos confirmar que el nivel actuó como piso (precio por encima y continúa)
    """
    if not candles:
        return False

    # buscamos toque
    touched = False
    closes: List[float] = []
    for i in range(min(len(candles), lookahead)):
        h = candles[i]["h"]
        l = candles[i]["l"]
        c = candles[i]["c"]
        if (l <= level <= h):
            touched = True
        if touched:
            closes.append(c)

    if not touched or len(closes) < 5:
        return False

    # 2 cierres a favor
    if direction == "down":
        # cierres por debajo
        ok2 = (closes[0] < level and closes[1] < level) or (closes[1] < level and closes[2] < level)
        if not ok2:
            return False
        # continuidad: mínimo nuevo relativo
        base_low = min(candles[i]["l"] for i in range(min(len(candles), lookahead)))
        # un “desplazamiento” mínimo: baja más allá de un umbral pequeño
        return base_low < (level - NAS_RULES["zone_buffer_points"] * 1.5)

    else:
        ok2 = (closes[0] > level and closes[1] > level) or (closes[1] > level and closes[2] > level)
        if not ok2:
            return False
        base_high = max(candles[i]["h"] for i in range(min(len(candles), lookahead)))
        return base_high > (level + NAS_RULES["zone_buffer_points"] * 1.5)


# =============================================================================
# 6) SOLO 3 GATILLOS PERMITIDOS (timing)
#    (a) Toque directo + cierre válido
#    (b) Barrida (perfora zona) + recuperación (cierra dentro/por el lado correcto)
#    (c) Ruptura de mínimo/máximo interno + retest fallido
#
# Nota: aquí no usamos nombres “de jerga”; describimos el evento.
# =============================================================================

def _last_n(candles: List[Dict[str, float]], n: int) -> List[Dict[str, float]]:
    return candles[-n:] if len(candles) >= n else candles[:]

def trigger_direct_touch_close(
    candles: List[Dict[str, float]],
    zone_low: float,
    zone_high: float,
    bias: str
) -> bool:
    """
    Toque directo: entra SOLO si hay cierre válido.
    - SELL: tocar zona y cerrar por debajo del zone_low (rechazo)
    - BUY:  tocar zona y cerrar por encima del zone_high (rechazo)
    """
    if len(candles) < 2:
        return False
    last = candles[-1]
    touched = (last["l"] <= zone_high and last["h"] >= zone_low)

    if not touched:
        return False

    if bias == "sell":
        return last["c"] < zone_low
    else:
        return last["c"] > zone_high

def trigger_sweep_reclaim(
    candles: List[Dict[str, float]],
    zone_low: float,
    zone_high: float,
    bias: str
) -> bool:
    """
    Barrida + recuperación:
    - SELL: perfora por arriba (h > zone_high) y luego cierra de vuelta por debajo de zone_high
    - BUY:  perfora por abajo (l < zone_low) y luego cierra de vuelta por encima de zone_low
    """
    if len(candles) < 2:
        return False
    a, b = candles[-2], candles[-1]

    if bias == "sell":
        swept = a["h"] > zone_high or b["h"] > zone_high
        reclaimed = b["c"] < zone_high
        return swept and reclaimed
    else:
        swept = a["l"] < zone_low or b["l"] < zone_low
        reclaimed = b["c"] > zone_low
        return swept and reclaimed

def trigger_break_retest(
    candles: List[Dict[str, float]],
    bias: str,
    internal_lookback: int = 12
) -> bool:
    """
    Ruptura + retest fallido (muy útil en NAS cuando la zona 100 está “sucia”):
    - SELL: rompe un mínimo interno (de los últimos N) y luego retestea sin recuperar
    - BUY:  rompe un máximo interno y luego retestea sin perder
    """
    if len(candles) < internal_lookback + 3:
        return False

    segment = candles[-(internal_lookback + 3):]
    prev = segment[:-3]
    x = segment[-3]  # vela de ruptura
    y = segment[-2]  # vela de retest
    z = segment[-1]  # confirmación

    prev_low = min(c["l"] for c in prev)
    prev_high = max(c["h"] for c in prev)

    if bias == "sell":
        broke = x["l"] < prev_low
        retest_fail = y["h"] <= prev_low and z["c"] <= prev_low
        return broke and retest_fail
    else:
        broke = x["h"] > prev_high
        retest_hold = y["l"] >= prev_high and z["c"] >= prev_high
        return broke and retest_hold


# =============================================================================
# 7) MOTOR “PLAN” NAS: dado sesgo + último impulso (A,B) y overshoot,
#    decide si ATLAS busca:
#    - Continuación (prioridad)
#    - Riesgo de transición (100 o más)
#    - NO_TRADE (si no llega a zona óptima o no hay timing)
# =============================================================================

def nas_pick_plan(
    bias: str,
    impulse_A: float,
    impulse_B: float,
    overshoot: float,
    exec_candles: List[Dict[str, float]],
    buffer_points: Optional[float] = None
) -> NASPlan:
    """
    bias: "sell" o "buy" (macro ya viene del sistema)
    impulse_A, impulse_B: últimos extremos del impulso dominante (para fibo del tramo)
    overshoot: ratio máximo alcanzado en corrección (>=0)
    exec_candles: velas del TF ejecución (M1/M3/M5), últimas velas
    """
    reasons: List[str] = []
    buffer_points = float(buffer_points if buffer_points is not None else NAS_RULES["zone_buffer_points"])

    # 1) zona objetivo por fibo 0.786 (siempre base en NAS)
    direction = "down" if bias == "sell" else "up"
    poi_0786 = fibo_price(impulse_A, impulse_B, NAS_RULES["poi_primary"], direction)
    zone_low, zone_high = make_zone(poi_0786, buffer_points)

    zone_class = classify_overshoot_zone(overshoot)
    strictness = timing_strictness(overshoot)

    # 2) lectura de estado por profundidad
    if zone_class == "lt_0786":
        # No llegó a zona óptima: tendencia fuerte
        return NASPlan(
            bias=bias,
            scenario="no_trade",
            zone_low=zone_low,
            zone_high=zone_high,
            entry_style="none",
            entry=None, sl=None, tp1=None, tp2=None,
            strictness="normal",
            reasons=[
                "No alcanzó 0.786: tendencia fuerte (no perseguir).",
                "Esperar siguiente tramo o próxima zona real de decisión."
            ]
        )

    if zone_class == "ge_100":
        reasons.append("Corrección alcanzó/ superó 100: alta prob. stop-hunt/transición → timing estricto.")
    else:
        reasons.append("Corrección en zona óptima (0.786–<100): mejor probabilidad de continuidad.")

    # 3) timing: SOLO 3 gatillos
    t1 = trigger_direct_touch_close(exec_candles, zone_low, zone_high, bias)
    t2 = trigger_sweep_reclaim(exec_candles, zone_low, zone_high, bias)
    t3 = trigger_break_retest(exec_candles, bias)

    entry_style = "none"
    if t2:
        entry_style = "sweep_reclaim"   # preferido cuando NAS se “pasa”
        reasons.append("Gatillo: barrida + recuperación (mejor para evitar SL obvio).")
    elif t1:
        entry_style = "direct_touch"
        reasons.append("Gatillo: toque directo + cierre válido.")
    elif t3 and strictness == "strict":
        entry_style = "break_retest"
        reasons.append("Gatillo: ruptura + retest fallido (modo estricto por zona 100+).")
    else:
        # si strict y no hay gatillo fuerte, NO_TRADE
        return NASPlan(
            bias=bias,
            scenario="no_trade",
            zone_low=zone_low,
            zone_high=zone_high,
            entry_style="none",
            entry=None, sl=None, tp1=None, tp2=None,
            strictness=strictness,
            reasons=reasons + ["No hubo timing válido. Silencio operativo."]
        )

    # 4) Niveles numéricos: entry/SL/TP (quirúrgico pero simple)
    # Entry:
    # - direct_touch: entry al cierre que confirma (última close)
    # - sweep_reclaim: entry al cierre de recuperación (última close)
    # - break_retest: entry al cierre de confirmación (última close)
    entry = exec_candles[-1]["c"]

    # SL: técnico corto según estilo (NAS = stops deben ser “estructurales”, no decorativos)
    if bias == "sell":
        # SL arriba del zone_high (y si sweep, arriba de la barrida reciente)
        recent_high = max(c["h"] for c in _last_n(exec_candles, 6))
        sl = max(zone_high + buffer_points * 0.8, recent_high + buffer_points * 0.3)
        # TP1: puntos típicos
        tp1 = entry - NAS_RULES["tp1_points_band"][0]
        tp2 = entry - NAS_RULES["tp1_points_band"][1]
    else:
        recent_low = min(c["l"] for c in _last_n(exec_candles, 6))
        sl = min(zone_low - buffer_points * 0.8, recent_low - buffer_points * 0.3)
        tp1 = entry + NAS_RULES["tp1_points_band"][0]
        tp2 = entry + NAS_RULES["tp1_points_band"][1]

    # 5) escenario final
    scenario = "continuation" if zone_class == "between_0786_and_lt_100" else "transition_risk"

    # 6) reglas de gestión textual para ATLAS
    reasons += [
        f"Zona: 0.786 con buffer {buffer_points:.1f} pts.",
        f"Strictness: {strictness}.",
        "Gestión NAS: TP1 temprano + BE rápido. Si no paga rápido, salir.",
        "Deuda pagada = aceptación (toque+cierres+retest+continuidad), no solo reacción."
    ]

    return NASPlan(
        bias=bias,
        scenario=scenario,
        zone_low=zone_low,
        zone_high=zone_high,
        entry_style=entry_style,
        entry=round(entry, 2),
        sl=round(sl, 2),
        tp1=round(tp1, 2),
        tp2=round(tp2, 2),
        strictness=strictness,
        reasons=reasons
    )


# =============================================================================
# 8) SALIDA SIMPLE (para UI/logs): convertir plan a dict serializable
# =============================================================================

def plan_to_dict(p: NASPlan) -> Dict[str, Any]:
    return {
        "bias": p.bias,
        "scenario": p.scenario,
        "zone": {"low": p.zone_low, "high": p.zone_high},
        "entry_style": p.entry_style,
        "entry": p.entry,
        "sl": p.sl,
        "tp1": p.tp1,
        "tp2": p.tp2,
        "strictness": p.strictness,
        "reasons": p.reasons,
    }


# =============================================================================
# 9) MINI “RECETA” PARA USARLO (ejemplo conceptual)
# =============================================================================
"""
Ejemplo de uso dentro del motor doctrinal (conceptual):

from atlas.core.nasdaq_knowledge import nas_pick_plan, plan_to_dict

# 1) El sistema ya trae sesgo macro:
bias = "sell"  # ejemplo

# 2) El sistema ya identifica último impulso dominante (A,B) en M5:
impulse_A = last_swing_high
impulse_B = last_swing_low

# 3) El sistema mide overshoot (ratio de corrección vs impulso):
overshoot = measured_overshoot_ratio

# 4) Candles del TF ejecución (M1/M3/M5):
exec_candles = candles_m1[-50:]  # ejemplo

plan = nas_pick_plan(
    bias=bias,
    impulse_A=impulse_A,
    impulse_B=impulse_B,
    overshoot=overshoot,
    exec_candles=exec_candles,
)

return plan_to_dict(plan)  # para snapshot/UI/logs
"""
