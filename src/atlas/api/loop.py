from __future__ import annotations

from atlas.bot.symbol_universe import get_universe_config


class AtlasLoop:
    def __init__(self):
        cfg = get_universe_config()
        # Loop default: lista MT5 canónica (sin BTC)
        self.symbols = list(cfg.default_mt5_symbols)

    def get_symbols(self):
        return list(self.symbols)