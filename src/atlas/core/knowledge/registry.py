from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeRef:
    symbol: str
    module: str


ENABLE_BTC = os.getenv("ATLAS_ENABLE_BTC", "0").strip() == "1"

REGISTRY = {
    "USTEC_x100z": KnowledgeRef(symbol="USTEC_x100z", module="atlas.core.knowledge.symbols.ustec_x100z"),
    "XAUUSDz":     KnowledgeRef(symbol="XAUUSDz",     module="atlas.core.knowledge.symbols.xauusdz"),
    "EURUSDz":     KnowledgeRef(symbol="EURUSDz",     module="atlas.core.knowledge.symbols.eurusdz"),
    "USDJPYz":     KnowledgeRef(symbol="USDJPYz",     module="atlas.core.knowledge.symbols.usdjpyz"),
    "GBPUSDz":     KnowledgeRef(symbol="GBPUSDz",     module="atlas.core.knowledge.symbols.gbpusdz"),
}

# BTC queda como módulo histórico opcional (NO universo por defecto)
if ENABLE_BTC:
    REGISTRY["BTCUSDz"] = KnowledgeRef(symbol="BTCUSDz", module="atlas.core.knowledge.symbols.btcusdz")


# Aliases que resolvemos a keys del REGISTRY
ALIASES = {
    "NAS100z": "USTEC_x100z",
    "NAS100":  "USTEC_x100z",
    "USTEC":   "USTEC_x100z",
    "NASDAQ":  "USTEC_x100z",
    "US100":   "USTEC_x100z",

    "GOLD":  "XAUUSDz",
    "XAUUSD": "XAUUSDz",
}

if ENABLE_BTC:
    ALIASES["BTCUSD"] = "BTCUSDz"


def resolve_knowledge_key(symbol: str) -> str | None:
    s = (symbol or "").strip().upper()
    if not s:
        return None
    return ALIASES.get(s, s)