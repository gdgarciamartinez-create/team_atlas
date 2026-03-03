from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional
import time

@dataclass
class PaperPos:
    status: str = "flat"   # flat|open|closed
    entry: Optional[float] = None
    sl: Optional[float] = None
    be: Optional[float] = None
    partial_done: bool = False
    opened_ts: Optional[int] = None

class PaperManager:
    """
    Gestión universal:
    - Riesgo fijo lo define el plan (no abre órdenes reales)
    - Cuando el precio avanza +2% desde entry:
        cierra 1% (flag) y mueve SL a BE
        resto en run
    """
    def __init__(self):
        self.pos: Dict[str, PaperPos] = {}
        self.partial_be_activations = 0

    def get(self, symbol: str) -> PaperPos:
        return self.pos.setdefault(symbol, PaperPos())

    def open_if_valid(self, symbol: str, entry: float, sl: float) -> None:
        p = self.get(symbol)
        if p.status == "open":
            return
        p.status = "open"
        p.entry = float(entry)
        p.sl = float(sl)
        p.be = None
        p.partial_done = False
        p.opened_ts = int(time.time())

    def update(self, symbol: str, last_price: float) -> None:
        p = self.get(symbol)
        if p.status != "open" or p.entry is None:
            return

        # STOP (paper)
        if p.sl is not None:
            if (last_price <= p.sl and last_price < p.entry) or (last_price >= p.sl and last_price > p.entry):
                p.status = "closed"
                return

        # +2% rule
        if not p.partial_done:
            up = (last_price - p.entry) / p.entry
            down = (p.entry - last_price) / p.entry
            moved = max(up, down)
            if moved >= 0.02:
                p.partial_done = True
                p.be = p.entry
                p.sl = p.entry  # SL a BE (paper)
                self.partial_be_activations += 1