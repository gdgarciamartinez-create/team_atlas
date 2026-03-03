from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Optional
from .data_source import Candle
from .evaluator import evaluate as eval_single
from atlas.bot.planner import build_plan

@dataclass
class MTFResult:
    direction: str
    context_ok: bool
    zone: Tuple[float,float]
    trigger: str
    confidence: float
    entry: Optional[float]
    sl: Optional[float]
    tps: List[float]
    reason_code: str
    score: float
    h1: dict
    m5: dict

def evaluate_mtf(candles_h1: List[Candle], candles_m5: List[Candle]) -> MTFResult:
    h1 = eval_single(candles_h1)
    # Contexto manda: debe estar OK en H1 para permitir ejecución
    context_ok = (h1.reason_code == "OK")

    # Si no hay contexto, NO_TRADE directo
    if not context_ok:
        return MTFResult(
            direction=h1.direction,
            context_ok=False,
            zone=h1.zone,
            trigger="none",
            confidence=0.0,
            entry=None,
            sl=None,
            tps=[],
            reason_code=h1.reason_code if h1.reason_code != "OK" else "NO_CONTEXT",
            score=h1.score * 0.6,
            h1=h1.__dict__,
            m5={},
        )

    # Ejecución en M5: se evalúa y se exige gatillo A/B/C alineado con dirección H1
    m5 = eval_single(candles_m5)

    # si M5 contradice dirección, NO_TRADE
    if m5.direction != h1.direction:
        return MTFResult(
            direction=h1.direction,
            context_ok=True,
            zone=h1.zone,
            trigger="none",
            confidence=0.0,
            entry=None,
            sl=None,
            tps=[],
            reason_code="CONFLICT_DIRECTION",
            score=min(h1.score, m5.score) * 0.5,
            h1=h1.__dict__,
            m5=m5.__dict__,
        )

    # Reglas: M5 necesita gatillo real, y tocar zona 0.786–0.79 (del propio M5) o estar dentro de zona H1
    in_h1_zone = (h1.zone[0] <= candles_m5[-1].c <= h1.zone[1]) if candles_m5 and h1.zone != (0.0,0.0) else False
    zone_ok = (m5.touched or in_h1_zone)

    if m5.reason_code != "OK" or not zone_ok:
        # preferimos reason_code de m5, pero si falla por zona, marcamos NO_0_786_TOUCH
        rc = m5.reason_code
        if not zone_ok:
            rc = "NO_0_786_TOUCH"
        return MTFResult(
            direction=h1.direction,
            context_ok=True,
            zone=h1.zone,
            trigger="none",
            confidence=0.0,
            entry=None,
            sl=None,
            tps=[],
            reason_code=rc,
            score=min(h1.score, m5.score) * 0.7,
            h1=h1.__dict__,
            m5=m5.__dict__,
        )

    # Construir plan real con planner
    m5_levels = getattr(m5, "levels", {})
    plan = build_plan(candles_m5, h1.direction, h1.zone, m5_levels)

    if plan is None:
        return MTFResult(
            direction=h1.direction,
            context_ok=True,
            zone=h1.zone,
            trigger="none",
            confidence=0.0,
            entry=None,
            sl=None,
            tps=[],
            reason_code="RISK_NOT_FEASIBLE",
            score=min(h1.score, m5.score) * 0.6,
            h1=h1.__dict__,
            m5=m5.__dict__,
        )

    return MTFResult(
        direction=h1.direction,
        context_ok=True,
        zone=h1.zone,
        trigger=m5.trigger,
        confidence=m5.confidence,
        entry=plan.entry,
        sl=plan.sl,
        tps=plan.tps,
        reason_code="OK",
        score=round(0.55*h1.score + 0.45*m5.score, 4),
        h1=h1.__dict__,
        m5=m5.__dict__,
    )