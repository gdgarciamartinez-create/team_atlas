from __future__ import annotations

from atlas.bot.symbol_universe import get_universe_config


def pick_default_symbol(symbol: str | None) -> str:
    cfg = get_universe_config()
    s = (symbol or "").strip()
    if s:
        return s
    # Default seguro (sin BTC): el primero del canon (EURUSDz por lista)
    return cfg.default_mt5_symbols[0]