from __future__ import annotations

from atlas.bot.universe import mt5_symbol


# ==========================================================
# Mapping CANÓNICO base -> MT5 (sin BTC por regla de universo)
# ==========================================================

SYMBOLS = {
    "XAUUSD": mt5_symbol("XAUUSD"),        # XAUUSDz
    "NAS100": mt5_symbol("NAS100"),        # USTEC_x100z
    "EURUSD": mt5_symbol("EURUSD"),        # EURUSDz
    "GBPUSD": mt5_symbol("GBPUSD"),        # GBPUSDz
    "USDJPY": mt5_symbol("USDJPY"),        # USDJPYz
    "USDCHF": mt5_symbol("USDCHF"),
    "USDCAD": mt5_symbol("USDCAD"),
    "AUDUSD": mt5_symbol("AUDUSD"),
    "NZDUSD": mt5_symbol("NZDUSD"),
}

def to_mt5(symbol: str) -> str:
    s = (symbol or "").strip().upper()
    return SYMBOLS.get(s, mt5_symbol(s))