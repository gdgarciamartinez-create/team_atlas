from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List


# =========
# Canon ATLAS: una sola fuente de verdad
# =========

SYMBOL_SUFFIX: str = os.getenv("ATLAS_SYMBOL_SUFFIX", "z")


def mt5_symbol(base: str) -> str:
    """
    Convierte símbolo base (sin sufijo) a símbolo MT5 (con sufijo / broker-name).
    """
    b = (base or "").strip().upper()

    # NASDAQ: tu broker usa USTEC_x100z
    if b in ("NAS100", "USTEC", "US100", "NASDAQ"):
        return f"USTEC_x100{SYMBOL_SUFFIX}"

    # Oro
    if b == "XAUUSD":
        return f"XAUUSD{SYMBOL_SUFFIX}"

    # Forex majors típicos
    if len(b) == 6 and b.isalpha():
        return f"{b}{SYMBOL_SUFFIX}"

    # Si ya viene con sufijo o viene raro, lo devolvemos tal cual
    return base


# Universo dinámico (regla del proyecto):
# - incluir EUR* y USD*
# - excluir BTC
UNIVERSE_INCLUDE_PREFIXES: List[str] = ["EUR", "USD"]
UNIVERSE_EXCLUDE_CONTAINS: List[str] = ["BTC"]


# Lista default para dropdowns / ejemplos / endpoints.
# (No impide que luego uses AUTO y el scanner te entregue más EUR* y USD*)
DEFAULT_BASE_SYMBOLS: List[str] = [
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "USDCHF",
    "USDCAD",
    "AUDUSD",
    "NZDUSD",
    "XAUUSD",
    "NAS100",
]


DEFAULT_MT5_SYMBOLS: List[str] = [mt5_symbol(s) for s in DEFAULT_BASE_SYMBOLS]


@dataclass(frozen=True)
class UniverseConfig:
    suffix: str
    include_prefixes: List[str]
    exclude_contains: List[str]
    default_base_symbols: List[str]
    default_mt5_symbols: List[str]


def get_universe_config() -> UniverseConfig:
    return UniverseConfig(
        suffix=SYMBOL_SUFFIX,
        include_prefixes=list(UNIVERSE_INCLUDE_PREFIXES),
        exclude_contains=list(UNIVERSE_EXCLUDE_CONTAINS),
        default_base_symbols=list(DEFAULT_BASE_SYMBOLS),
        default_mt5_symbols=list(DEFAULT_MT5_SYMBOLS),
    )