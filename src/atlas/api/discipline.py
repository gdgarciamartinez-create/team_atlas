from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Tuple
import time

@dataclass
class Discipline:
    # 1 trade por símbolo por ventana
    traded_in_window: Dict[Tuple[str,str], bool] = field(default_factory=dict)
    # cooldown por símbolo (segundos)
    cooldown_until: Dict[str, int] = field(default_factory=dict)
    # expiración de setup (si pasa mucho sin trigger)
    setup_started_ts: Dict[str, int] = field(default_factory=dict)

    def can_consider(self, symbol: str, window: str) -> Tuple[bool,str]:
        now = int(time.time())
        if self.cooldown_until.get(symbol, 0) > now:
            return False, "COOLDOWN"
        if self.traded_in_window.get((symbol, window), False):
            return False, "WINDOW_LIMIT_REACHED"
        return True, "OK"

    def mark_setup_started(self, symbol: str) -> None:
        self.setup_started_ts.setdefault(symbol, int(time.time()))

    def is_setup_expired(self, symbol: str, max_age_s: int = 30*60) -> bool:
        now = int(time.time())
        start = self.setup_started_ts.get(symbol)
        if start is None:
            return False
        return (now - start) > max_age_s

    def mark_trade(self, symbol: str, window: str) -> None:
        self.traded_in_window[(symbol, window)] = True
        # cooldown corto para evitar spam
        self.cooldown_until[symbol] = int(time.time()) + 5*60
        # reset setup timer
        if symbol in self.setup_started_ts:
            del self.setup_started_ts[symbol]

    def reset_window(self, window: str) -> None:
        # limpia flags de esa ventana (cuando cambia la ventana activa)
        keys = [k for k in self.traded_in_window.keys() if k[1] == window]
        for k in keys:
            del self.traded_in_window[k]
