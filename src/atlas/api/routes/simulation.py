from __future__ import annotations
from dataclasses import dataclass
from typing import Dict
import time

@dataclass
class SimAccount:
    balance: float = 10000.0
    currency: str = "USD"
    trades_analyzed: int = 0
    wins: int = 0
    losses: int = 0
    total_rr: float = 0.0
    updated_ts: int = 0

    @property
    def winrate(self) -> float:
        if self.trades_analyzed == 0:
            return 0.0
        return round((self.wins / self.trades_analyzed) * 100.0, 1)

    @property
    def avg_rr(self) -> float:
        if self.trades_analyzed == 0:
            return 0.0
        return round(self.total_rr / self.trades_analyzed, 2)

SIM = SimAccount()

def sim_snapshot() -> Dict:
    return {
        "balance": SIM.balance,
        "currency": SIM.currency,
        "trades": SIM.trades_analyzed,
        "wins": SIM.wins,
        "losses": SIM.losses,
        "winrate": SIM.winrate,
        "avg_rr": SIM.avg_rr,
        "updated_ts": SIM.updated_ts,
    }

def sim_touch(rr: float, win: bool) -> None:
    # NO se usa para trading real. Solo laboratorio.
    SIM.trades_analyzed += 1
    if win:
        SIM.wins += 1
    else:
        SIM.losses += 1
    SIM.total_rr += float(rr)
    SIM.updated_ts = int(time.time())