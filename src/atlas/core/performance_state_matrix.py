from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional
import statistics
import time


@dataclass
class TradeRecord:
    ts: float
    symbol: str
    state: str
    zone_used: str
    trigger: str
    result_R: float
    time_to_tp1_minutes: float
    hit_tp1: bool
    hit_sl: bool


class PerformanceMatrix:
    def __init__(self, max_records: int = 50000):
        self.max_records = int(max_records)
        self.trades: List[TradeRecord] = []

    def add_trade(self, record: TradeRecord) -> None:
        self.trades.append(record)
        if len(self.trades) > self.max_records:
            self.trades = self.trades[-self.max_records :]

    def add_trade_simple(
        self,
        symbol: str,
        state: str,
        zone_used: str,
        trigger: str,
        result_R: float,
        time_to_tp1_minutes: float,
        hit_tp1: bool,
        hit_sl: bool,
        ts: Optional[float] = None,
    ) -> None:
        self.add_trade(
            TradeRecord(
                ts=float(ts if ts is not None else time.time()),
                symbol=str(symbol).upper(),
                state=str(state),
                zone_used=str(zone_used),
                trigger=str(trigger),
                result_R=float(result_R),
                time_to_tp1_minutes=float(time_to_tp1_minutes),
                hit_tp1=bool(hit_tp1),
                hit_sl=bool(hit_sl),
            )
        )

    def _filter(self, symbol: Optional[str] = None, state: Optional[str] = None) -> List[TradeRecord]:
        data = self.trades
        if symbol:
            sym = symbol.upper()
            data = [t for t in data if t.symbol == sym]
        if state:
            data = [t for t in data if t.state == state]
        return data

    def summary(self, symbol: Optional[str] = None, state: Optional[str] = None) -> Dict[str, Any]:
        data = self._filter(symbol, state)
        if not data:
            return {"message": "No data", "trades": 0}

        results = [t.result_R for t in data]
        tp1_hits = sum(1 for t in data if t.hit_tp1)
        sl_hits = sum(1 for t in data if t.hit_sl)
        ttp1 = [t.time_to_tp1_minutes for t in data if t.hit_tp1]

        return {
            "trades": len(data),
            "winrate_tp1": tp1_hits / len(data),
            "sl_rate": sl_hits / len(data),
            "avg_R": statistics.mean(results),
            "median_R": statistics.median(results),
            "avg_time_to_tp1": (statistics.mean(ttp1) if ttp1 else None),
        }

    def matrix_by_symbol_and_state(self) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        for t in self.trades:
            out.setdefault(t.symbol, {})
            if t.state not in out[t.symbol]:
                out[t.symbol][t.state] = self.summary(symbol=t.symbol, state=t.state)
        return out

    def recent(self, n: int = 50) -> List[Dict[str, Any]]:
        return [asdict(t) for t in self.trades[-int(n):]]
