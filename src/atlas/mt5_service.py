from __future__ import annotations
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("atlas.mt5")

try:
    import MetaTrader5 as mt5
except Exception:
    mt5 = None

TF_MAP = {"M1": 1, "M5": 5, "M15": 15}

class MT5Service:
    def __init__(self) -> None:
        if mt5 is None:
            raise RuntimeError("MetaTrader5 no disponible. Instala: pip install MetaTrader5")
        self._init_ok = False

    def init(self) -> bool:
        if self._init_ok:
            return True
        ok = mt5.initialize()
        self._init_ok = bool(ok)
        if not ok:
            logger.error("MT5 initialize() falló")
        return self._init_ok

    def symbol_info(self, symbol: str):
        self.init()
        return mt5.symbol_info(symbol)

    def last_price(self, symbol: str) -> Optional[float]:
        self.init()
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return None
        return float(tick.ask) if tick.ask else float(tick.bid)

    def rates(self, symbol: str, tf: str, n: int = 160) -> List[Dict[str, Any]]:
        self.init()
        tf_min = TF_MAP.get(tf)
        if tf_min is None:
            raise ValueError(f"TF no soportado: {tf}")
        mt5_tf = getattr(mt5, f"TIMEFRAME_M{tf_min}")
        rates = mt5.copy_rates_from_pos(symbol, mt5_tf, 0, n)
        if rates is None:
            return []
        out = []
        for r in rates:
            out.append({
                "time": int(r["time"]),
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
                "tick_volume": int(r["tick_volume"]),
            })
        return out

    def tick_value_per_point(self, symbol: str) -> Optional[float]:
        info = self.symbol_info(symbol)
        if info is None:
            return None
        tick_value = float(getattr(info, "trade_tick_value", 0.0) or 0.0)
        tick_size  = float(getattr(info, "trade_tick_size", 0.0) or 0.0)
        point      = float(getattr(info, "point", 0.0) or 0.0)
        if tick_value <= 0 or tick_size <= 0 or point <= 0:
            return None
        value_per_price_unit = tick_value / tick_size
        value_per_point = value_per_price_unit * point
        return value_per_point
