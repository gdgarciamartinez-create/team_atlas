from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any
import time

import MetaTrader5 as mt5

@dataclass
class ExecResult:
    ok: bool
    error: Optional[str] = None
    order_id: Optional[int] = None
    details: Optional[Dict[str, Any]] = None

class MT5Executor:
    def __init__(self):
        self.initialized = False

    def init(self) -> bool:
        if self.initialized:
            return True
        if not mt5.initialize():
            return False
        self.initialized = True
        return True

    def ensure_symbol(self, symbol: str) -> bool:
        if not mt5.symbol_select(symbol, True):
            return False
        return True

    def place_market_order(
        self,
        symbol: str,
        side: str,               # BUY|SELL
        lots: float,
        sl: float,
        tp: Optional[float] = None,
        deviation: int = 20,
        magic: int = 20260208,
        comment: str = "ATLAS",
    ) -> ExecResult:
        if not self.init():
            return ExecResult(ok=False, error="MT5 initialize failed")
        if not self.ensure_symbol(symbol):
            return ExecResult(ok=False, error=f"symbol_select failed: {symbol}")

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return ExecResult(ok=False, error="no tick")

        price = tick.ask if side == "BUY" else tick.bid
        order_type = mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL

        req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(lots),
            "type": order_type,
            "price": float(price),
            "sl": float(sl),
            "tp": float(tp) if tp is not None else 0.0,
            "deviation": int(deviation),
            "magic": int(magic),
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        res = mt5.order_send(req)
        if res is None:
            return ExecResult(ok=False, error="order_send returned None")

        if res.retcode != mt5.TRADE_RETCODE_DONE:
            return ExecResult(ok=False, error=f"retcode={res.retcode}", details=res._asdict())

        return ExecResult(ok=True, order_id=int(res.order), details=res._asdict())