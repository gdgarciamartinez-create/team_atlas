from __future__ import annotations

from fastapi import APIRouter

from atlas.bot.symbol_universe import mt5_symbol

router = APIRouter(prefix="/world_config", tags=["world_config"])

# Defaults por mundo (base), luego pasamos a MT5 por mt5_symbol()
WORLD_DEFAULTS_BASE = {
    "GENERAL":   {"tf": "M5", "symbol": "EURUSD"},
    "PRESESION": {"tf": "M5", "symbol": "XAUUSD"},  # default oro
    "GAP":       {"tf": "M1", "symbol": "XAUUSD"},
    "GATILLOS":  {"tf": "M3", "symbol": "EURUSD"},
    "ATLAS_IA":  {"tf": "M5", "symbol": "EURUSD"},
}

GATILLOS_SYMBOLS_BASE = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]


@router.get("")
def get_world_config():
    worlds = {}
    for k, v in WORLD_DEFAULTS_BASE.items():
        worlds[k] = {
            "tf": v["tf"],
            "symbol_base": v["symbol"],
            "symbol": mt5_symbol(v["symbol"]),
        }

    return {
        "worlds": worlds,
        "gatillos_symbols_base": list(GATILLOS_SYMBOLS_BASE),
        "gatillos_symbols": [mt5_symbol(s) for s in GATILLOS_SYMBOLS_BASE],
    }