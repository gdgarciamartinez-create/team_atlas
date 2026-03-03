from __future__ import annotations
from dataclasses import dataclass
from typing import TypedDict, Optional, Literal, Dict, Any, List


Direction = Literal["UP", "DOWN"]


@dataclass(frozen=True)
class POI:
    """
    Point Of Interest / zona operable.
    low/high: límites de la zona.
    direction: sesgo esperado al reaccionar en la zona ("UP" o "DOWN").
    meta: info adicional (ej: motivo, tf, tags).
    """
    low: float
    high: float
    direction: Direction
    meta: Dict[str, Any] | None = None


class Decision(TypedDict, total=False):
    """
    Decisión final del motor.
    """
    action: Literal["TRADE", "NO_TRADE"]
    side: Optional[Literal["BUY", "SELL"]]
    entry: Optional[float]
    sl: Optional[float]
    tp: Optional[float]
    reason: str
    tags: List[str]
    confidence: float
    checklist: Optional[Dict[str, Any]]
