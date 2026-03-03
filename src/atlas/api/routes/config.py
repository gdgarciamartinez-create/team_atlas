from __future__ import annotations

import os
from fastapi import APIRouter

from atlas.bot.symbol_universe import get_universe_config

router = APIRouter(prefix="/config", tags=["config"])


def _env_list(name: str, default_csv: str) -> list[str]:
    raw = os.getenv(name, default_csv)
    out = []
    for x in (raw or "").split(","):
        s = x.strip()
        if s:
            out.append(s)
    return out


@router.get("")
def get_config() -> dict:
    cfg = get_universe_config()

    # Whitelist MT5 por defecto: SIN BTC, con sufijo z y NAS100→USTEC_x100z
    default_whitelist = ",".join(cfg.default_mt5_symbols)

    symbol_whitelist = _env_list("ATLAS_SYMBOL_WHITELIST", default_whitelist)

    return {
        "symbol_suffix": cfg.suffix,
        "universe": {
            "include_prefixes": cfg.include_prefixes,
            "exclude_contains": cfg.exclude_contains,
        },
        "defaults": {
            "base_symbols": cfg.default_base_symbols,
            "mt5_symbols": cfg.default_mt5_symbols,
        },
        "symbol_whitelist": symbol_whitelist,
    }