from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple
from .data_source import Candle

@dataclass
class CorrectionCheck:
    depth_ok: bool
    slow_ok: bool
    momentum_ok: bool
    valid: bool

def correction_quality(candles: List[Candle], direction: str, zone: Tuple[float,float], max_violent_bodies: int = 2) -> CorrectionCheck:
    """
    Objetivo: validar corrección sin inventar.
    - depth_ok: zona 0.5+ (en nuestro sistema viene de tocar 0.786/0.79)
    - slow_ok: corrección no violenta (no demasiadas velas de cuerpo grande)
    - momentum_ok: desaceleración (cuerpos decrecientes en las últimas velas)
    """
    if len(candles) < 20:
        return CorrectionCheck(False, False, False, False)

    tail = candles[-12:]
    bodies = [abs(c.c - c.o) for c in tail]
    avg_body = sum(bodies) / max(1, len(bodies))

    # violenta si muchas velas superan 1.6x el promedio
    violent = sum(1 for b in bodies if b > avg_body * 1.6)
    slow_ok = violent <= max_violent_bodies

    # momentum_ok: últimos 4 cuerpos en promedio menores que los 4 anteriores
    last4 = sum(bodies[-4:]) / 4.0
    prev4 = sum(bodies[-8:-4]) / 4.0
    momentum_ok = last4 < prev4

    # depth_ok: si el close actual está en zona, asumimos profundidad suficiente por diseño
    zlo, zhi = zone
    depth_ok = zlo <= candles[-1].c <= zhi

    valid = depth_ok and slow_ok and momentum_ok
    return CorrectionCheck(depth_ok, slow_ok, momentum_ok, valid)
