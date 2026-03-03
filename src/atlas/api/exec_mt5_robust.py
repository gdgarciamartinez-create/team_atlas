from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any
import time
import MetaTrader5 as mt5

from .resilience import with_retry, RetryPolicy
from .config import normalize_lots, SYMBOL_CFG

@dataclass
class ExecResult:
    ok: bool
    error: Optional[str] = None
    order_id: Optional[int] = None
    details: Optional[Dict[str, Any]] = None

class MT5ExecutorRobust:
    def __init__(self):
        self.initialized = False
        self.policy = RetryPolicy(tries=3, base_delay_s=0.5, max_delay_s=4.0)

    def init(self) -> bool:
        if self.initialized:
            return True
        ok = mt5.initialize()
        self.initialized = bool(ok)
        return self.initialized

    def _ensure(self, symbol: str) -> None:
        if not self.init():
            raise RuntimeError("MT5_INIT_FAIL")
        if not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"SYMBOL_SELECT_FAIL:{symbol}")

    def _spread_ok(self, symbol: str) -> bool:
        cfg = SYMBOL_CFG.get(symbol)
        if not cfg or cfg.max_spread_points is None:
            return True
        info = mt5.symbol_info(symbol)
        if not info:
            return True
        # spread en puntos (broker)
        spr = float(info.spread)
        return spr <= float(cfg.max_spread_points)

    def place_market(self, symbol: str, side: str, lots: float, sl: float, tp: Optional[float] = None, deviation: int = 20) -> ExecResult:
        try:
            def go():
                self._ensure(symbol)
                if not self._spread_ok(symbol):
                    raise RuntimeError("SPREAD_TOO_HIGH")

                tick = mt5.symbol_info_tick(symbol)
                if tick is None:
                    raise RuntimeError("NO_TICK")

                lots_n = normalize_lots(symbol, lots)
                price = tick.ask if side == "BUY" else tick.bid
                order_type = mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL

                req = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": float(lots_n),
                    "type": order_type,
                    "price": float(price),
                    "sl": float(sl),
                    "tp": float(tp) if tp is not None else 0.0,
                    "deviation": int(deviation),
                    "magic": 20260208,
                    "comment": "ATLAS_EXEC",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }
                res = mt5.order_send(req)
                if res is None:
                    raise RuntimeError("ORDER_SEND_NONE")
                if res.retcode != mt5.TRADE_RETCODE_DONE:
                    raise RuntimeError(f"RET:{res.retcode}")
                return res

            res = with_retry(go, self.policy)
            return ExecResult(ok=True, order_id=int(res.order), details=res._asdict())
        except Exception as e:
            return ExecResult(ok=False, error=str(e))