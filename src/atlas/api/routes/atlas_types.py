from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class POI:
    symbol: str
    side: str        # BUY / SELL
    trigger: str     # texto corto
    entry: float
    sl: float
    parcial: float
    tp2: float
    rr_tp2: float
    lot_sim: float
    tf: str
    world: str
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "trigger": self.trigger,
            "entry": self.entry,
            "sl": self.sl,
            "parcial": self.parcial,
            "tp2": self.tp2,
            "rr_tp2": self.rr_tp2,
            "lot_sim": self.lot_sim,
            "tf": self.tf,
            "world": self.world,
            "note": self.note,
        }

@dataclass
class Decision:
    confirmed: bool
    state_tag: str     # CONFIRMED / WAIT / NO_TRADE
    reason: str        # razón corta
    checklist: Dict[str, bool]
    fibo: Dict[str, Any]
    poi: Optional[POI] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "confirmed": self.confirmed,
            "state_tag": self.state_tag,
            "reason": self.reason,
            "checklist": self.checklist,
            "fibo": self.fibo,
            "poi": self.poi.to_dict() if self.poi else None,
        }