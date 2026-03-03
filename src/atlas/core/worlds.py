from typing import Dict, List

# IMPORTANTÍSIMO: broker usa sufijo z
# (si mañana cambia, se cambia acá y listo)
BROKER_SUFFIX = "z"

def z(sym: str) -> str:
    sym = sym.strip()
    if sym.upper().endswith(BROKER_SUFFIX.upper()):
        return sym
    return f"{sym}{BROKER_SUFFIX}"

WORLD_GAP = "GAP"
WORLD_PRESESION = "PRESESION"
WORLD_GATILLO = "GATILLO"
WORLD_ATLAS_IA = "ATLAS_IA"

# PRESESION: EUR* + USD* (sin BTC)
PRESESION_PAIRS: List[str] = list(map(z, [
    "EURUSD","EURJPY","EURAUD","EURCAD","EURNZD","EURCHF","EURGBP",
    "USDJPY","USDCAD","USDCHF",
    "GBPUSD","AUDUSD","NZDUSD",
]))

# GAP: solo oro
GAP_PAIRS: List[str] = [z("XAUUSD")]

# ATLAS IA: 2 islas, 4 pares cada una
ATLAS_SCALPING: List[str] = [
    z("XAUUSD"),
    z("EURUSD"),
    z("USOIL"),
    z("USTEC_x100"),   # tu NASDAQ del broker: USTEC_x100z
]
ATLAS_FOREX: List[str] = [
    z("XAUUSD"),
    z("EURUSD"),
    z("USDJPY"),
    z("GBPUSD"),
]

# GATILLO: arranca con estos, después lo llenás con parámetros
GATILLO_DEFAULT: List[str] = [
    z("XAUUSD"),
    z("EURUSD"),
    z("USOIL"),
    z("USTEC_x100"),
]

WORLDS: Dict[str, Dict] = {
    WORLD_GAP: {
        "pairs": GAP_PAIRS,
        "tf_default": "M1",
        "symbol_default": z("XAUUSD"),
        "fixed_symbol": True,
    },
    WORLD_PRESESION: {
        "pairs": PRESESION_PAIRS,
        "tf_default": "M5",
        "symbol_default": PRESESION_PAIRS[0],
        "fixed_symbol": False,
    },
    WORLD_GATILLO: {
        "pairs": GATILLO_DEFAULT,
        "tf_default": "M3",
        "symbol_default": z("XAUUSD"),
        "fixed_symbol": False,
    },
    WORLD_ATLAS_IA: {
        "pairs": list(sorted(set(ATLAS_SCALPING + ATLAS_FOREX))),
        "tf_default": "M5",
        "symbol_default": z("XAUUSD"),
        "fixed_symbol": False,
    },
}