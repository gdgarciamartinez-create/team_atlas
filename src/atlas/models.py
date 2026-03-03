from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Optional, Literal, List, Dict, Any
import time
import uuid

Direction = Literal["buy", "sell"]
Mode = Literal["gatillo", "gap", "presesion"]

@dataclass
class Setup:
    id: str
    symbol: str
    direction: Direction
    zone_low: float
    zone_high: float
    tfs: List[str]
    mode: Mode
    enabled: bool = True
    sl: Optional[float] = None
    tp1: Optional[float] = None
    tp2: Optional[float] = None
    notes: str = ""
    created_at: float = 0.0

    @staticmethod
    def new(**kwargs) -> "Setup":
        return Setup(id=str(uuid.uuid4())[:8], created_at=time.time(), **kwargs)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class Proposal:
    symbol: str
    direction: Direction
    tf: str
    mode: Mode
    gatillo: str
    entry: float
    sl: float
    tp1: float
    tp2: float
    partial_pct: int
    lots: float
    rr_tp1: float
    rr_tp2: float
    fib_ok: bool
    context: Dict[str, Any]

@dataclass
class AIResult:
    ok: bool
    reason: str
