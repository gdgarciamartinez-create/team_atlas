from __future__ import annotations
from typing import Tuple

try:
    import MetaTrader5 as mt5
except Exception:
    mt5 = None

def calc_lot_1pct(symbol: str, entry: float, sl: float, balance: float = 10000.0, risk_pct: float = 0.01) -> Tuple[float, str]:
    risk_money = balance * risk_pct
    dist = abs(entry - sl)
    if dist <= 0:
        return 0.01, "LOT_FALLBACK_DIST0"

    if mt5 is None:
        return 0.01, "LOT_FALLBACK_NO_MT5_MODULE"

    try:
        info = mt5.symbol_info(symbol)
        if info is None:
            return 0.01, "LOT_FALLBACK_NO_SYMBOL_INFO"

        tick_val = getattr(info, "trade_tick_value", None)
        tick_size = getattr(info, "trade_tick_size", None)
        if not tick_val or not tick_size:
            return 0.01, "LOT_FALLBACK_NO_TICK"

        ticks = dist / float(tick_size)
        risk_per_lot = ticks * float(tick_val)
        if risk_per_lot <= 0:
            return 0.01, "LOT_FALLBACK_BAD_TICK"

        lot = risk_money / risk_per_lot
        lot = max(0.01, min(float(lot), 50.0))
        return round(lot, 2), "LOT_OK_MT5"
    except Exception:
        return 0.01, "LOT_FALLBACK_EXCEPTION"