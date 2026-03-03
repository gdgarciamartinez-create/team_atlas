from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any
import time

@dataclass
class SimAccount:
    balance: float = 10000.0
    risk_pct: float = 0.01
    analyzed: int = 0
    rr_sum: float = 0.0
    last_ts: int = field(default_factory=lambda: int(time.time()))

    def snapshot(self) -> Dict[str, Any]:
        avg_rr = (self.rr_sum / self.analyzed) if self.analyzed else 0.0
        return {
            "balance": round(self.balance, 2),
            "risk_pct": self.risk_pct,
            "analyzed": self.analyzed,
            "avg_rr": round(avg_rr, 2),
            "ts": self.last_ts,
        }

SIM = SimAccount()

def get_sim_stats() -> Dict[str, Any]:
    return SIM.snapshot()

def add_analyzed(rr: float) -> None:
    SIM.analyzed += 1
    SIM.rr_sum += float(rr)
    SIM.last_ts = int(time.time())