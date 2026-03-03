import MetaTrader5 as mt5
from datetime import datetime
from typing import List, Dict

class MT5Feed:
    def __init__(self):
        self.connected = False

    def connect(self) -> bool:
        if mt5.initialize():
            self.connected = True
            return True
        self.connected = False
        return False

    def shutdown(self):
        if self.connected:
            mt5.shutdown()
            self.connected = False

    def candles(self, symbol: str, timeframe=mt5.TIMEFRAME_M1, n=200) -> List[Dict]:
        if not self.connected:
            if not self.connect():
                return []

        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n)
        if rates is None:
            return []

        candles = []
        for r in rates:
            candles.append({
                "time": int(r["time"]),
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
            })
        return candles