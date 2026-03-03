import os
from dataclasses import dataclass
from typing import Optional, Dict, Any

EXEC_ENABLED = os.getenv("ATLAS_EXEC_ENABLED", "false").lower() == "true"

try:
    import MetaTrader5 as mt5
except Exception:
    mt5 = None

@dataclass
class ExecResult:
    ok: bool
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class MT5Executor:
    def __init__(self):
        self.armed = False

    def status(self) -> Dict[str, Any]:
        if mt5 is None:
            return {"ok": False, "error": "MT5_PYTHON_PACKAGE_MISSING"}
        if not mt5.initialize():
            return {"ok": False, "error": "MT5_NOT_INITIALIZED"}
        info = mt5.terminal_info()
        acc = mt5.account_info()
        mt5.shutdown()
        return {
            "ok": True,
            "terminal": str(info),
            "account": str(acc),
            "exec_enabled": EXEC_ENABLED,
            "armed": self.armed,
        }

    def set_armed(self, armed: bool):
        self.armed = bool(armed)

    def place_market(self, symbol: str, side: str, lots: float, sl: float, tp: float, magic: int, deviation: int) -> ExecResult:
        if not EXEC_ENABLED:
            return ExecResult(ok=False, error="EXEC_DISABLED")
        if not self.armed:
            return ExecResult(ok=False, error="NOT_ARMED")
        if mt5 is None:
            return ExecResult(ok=False, error="MT5_PYTHON_PACKAGE_MISSING")

        if not mt5.initialize():
            return ExecResult(ok=False, error="MT5_NOT_INITIALIZED")

        # ensure symbol selected
        if not mt5.symbol_select(symbol, True):
            mt5.shutdown()
            return ExecResult(ok=False, error="SYMBOL_NOT_FOUND_OR_NOT_SELECTED", details={"symbol": symbol})

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            mt5.shutdown()
            return ExecResult(ok=False, error="NO_TICK", details={"symbol": symbol})

        side = side.upper()
        order_type = mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL
        price = tick.ask if side == "BUY" else tick.bid

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(lots),
            "type": order_type,
            "price": float(price),
            "sl": float(sl),
            "tp": float(tp),
            "deviation": int(deviation),
            "magic": int(magic),
            "comment": "ATLAS",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        res = mt5.order_send(request)
        mt5.shutdown()

        if res is None:
            return ExecResult(ok=False, error="ORDER_SEND_FAILED_NULL")
        if res.retcode != mt5.TRADE_RETCODE_DONE:
            return ExecResult(ok=False, error="ORDER_REJECTED", details={"retcode": res.retcode, "comment": str(res.comment)})

        return ExecResult(ok=True, details={"order": res._asdict()})