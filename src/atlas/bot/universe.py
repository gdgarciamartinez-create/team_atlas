from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List


# ==========================================================
# CANON ÚNICO TEAM ATLAS — Universo + Sufijo + Mapping MT5
# ==========================================================

SYMBOL_SUFFIX: str = os.getenv("ATLAS_SYMBOL_SUFFIX", "z")

# Regla proyecto:
# Universo ventanas: todos EUR* y USD* excluyendo BTC
UNIVERSE_INCLUDE_PREFIXES: List[str] = ["EUR", "USD"]
UNIVERSE_EXCLUDE_CONTAINS: List[str] = ["BTC"]

# Defaults para UI / endpoints / demos (base, sin sufijo)
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


def mt5_symbol(base: str) -> str:
    """
    Convierte símbolo base a símbolo MT5:
    - Añade sufijo z
    - NAS100 => USTEC_x100z (tu broker)
    """
    b = (base or "").strip().upper()

    if b in ("NAS100", "USTEC", "US100", "NASDAQ"):
        return f"USTEC_x100{SYMBOL_SUFFIX}"

    if b == "XAUUSD":
        return f"XAUUSD{SYMBOL_SUFFIX}"

    # Forex típicos: 6 letras
    if len(b) == 6 and b.isalpha():
        return f"{b}{SYMBOL_SUFFIX}"

    # Si ya venía raro o ya venía con sufijo, lo devolvemos
    return base


DEFAULT_MT5_SYMBOLS: List[str] = [mt5_symbol(s) for s in DEFAULT_BASE_SYMBOLS]


def is_allowed_by_universe(symbol_any: str) -> bool:
    """
    Filtro duro:
    - Excluye BTC siempre
    - Acepta EUR* y USD*
    - Oro/NAS100 quedan fuera del filtro por prefijos, así que se permiten por excepción.
    """
    s = (symbol_any or "").strip().upper()

    # excluye si contiene "BTC"
    for bad in UNIVERSE_EXCLUDE_CONTAINS:
        if bad in s:
            return False

    # permitir excepciones del proyecto
    if "XAUUSD" in s or "USTEC" in s or "NAS100" in s:
        return True

    # permitir EUR* o USD*
    return any(s.startswith(p) for p in UNIVERSE_INCLUDE_PREFIXES)


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