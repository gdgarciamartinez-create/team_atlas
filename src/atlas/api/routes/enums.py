from __future__ import annotations

from atlas.bot.symbol_universe import get_universe_config


cfg = get_universe_config()

# Lista base visible para UI / endpoints (sin sufijo)
BASE_SYMBOLS = cfg.default_base_symbols

# Lista MT5 (con sufijo y mapping broker)
MT5_SYMBOLS = cfg.default_mt5_symbols