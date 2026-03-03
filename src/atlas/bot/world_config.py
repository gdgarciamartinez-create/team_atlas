# src/atlas/world_config.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


# ============================================================
# TEAM ATLAS — Single Source of Truth for:
# - symbol suffix
# - universos por mundo
# - activos especiales (XAU separado)
# ============================================================

SYMBOL_SUFFIX = "z"

# Oro separado (activo especial)
XAU_SYMBOL = f"XAUUSD{SYMBOL_SUFFIX}"

# Universo base FX:
# Regla: pares EUR* y USD* (excluye BTC)
# Nota: acá listamos los "core" más usados; si querés ampliar,
# se amplía SOLO en este archivo.
FX_UNIVERSE_CORE: List[str] = [
    f"EURUSD{SYMBOL_SUFFIX}",
    f"EURGBP{SYMBOL_SUFFIX}",
    f"EURJPY{SYMBOL_SUFFIX}",
    f"EURCHF{SYMBOL_SUFFIX}",
    f"EURAUD{SYMBOL_SUFFIX}",
    f"EURCAD{SYMBOL_SUFFIX}",
    f"EURNZD{SYMBOL_SUFFIX}",
    f"GBPUSD{SYMBOL_SUFFIX}",
    f"USDJPY{SYMBOL_SUFFIX}",
    f"USDCHF{SYMBOL_SUFFIX}",
    f"USDCAD{SYMBOL_SUFFIX}",
    f"AUDUSD{SYMBOL_SUFFIX}",
    f"NZDUSD{SYMBOL_SUFFIX}",
]

# Si tu broker tiene nombres distintos (ej: USTEC_x100z),
# se agregan como "extra symbols" por separado (NO rompe la regla FX).
EXTRA_SYMBOLS: List[str] = [
    f"USTEC_x100{SYMBOL_SUFFIX}",
]

# Map de mundos -> símbolos habilitados
# (mantenemos XAU separado para que el motor lo trate distinto)
WORLD_SYMBOLS: Dict[str, Dict[str, List[str]]] = {
    "ATLAS_IA": {
        "fx": FX_UNIVERSE_CORE,
        "xau": [XAU_SYMBOL],
        "extra": EXTRA_SYMBOLS,
    },
    # Otros mundos si los usás:
    "GAP": {
        "fx": [],
        "xau": [XAU_SYMBOL],
        "extra": [],
    },
    "PRESESIÓN": {
        "fx": FX_UNIVERSE_CORE,
        "xau": [],
        "extra": EXTRA_SYMBOLS,
    },
}


@dataclass(frozen=True)
class Universe:
    fx: List[str]
    xau: List[str]
    extra: List[str]


def get_universe(world: str) -> Universe:
    w = (world or "").strip() or "ATLAS_IA"
    if w not in WORLD_SYMBOLS:
        w = "ATLAS_IA"
    block = WORLD_SYMBOLS[w]
    return Universe(
        fx=list(block.get("fx", [])),
        xau=list(block.get("xau", [])),
        extra=list(block.get("extra", [])),
    )


def get_all_symbols(world: str) -> List[str]:
    u = get_universe(world)
    # Orden: XAU primero si existe (por prioridad), luego FX, luego extras
    return list(u.xau) + list(u.fx) + list(u.extra)


def is_xau(symbol: str) -> bool:
    return (symbol or "").strip().upper() == XAU_SYMBOL.upper()