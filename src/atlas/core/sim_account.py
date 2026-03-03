# src/atlas/core/sim_account.py
from __future__ import annotations
from typing import Any, Dict, Optional
import time

_SIM: Dict[str, Any] = {
    "balance": 10000.0,
    "equity": 10000.0,
    "trades": 0,
    "wins": 0,
    "losses": 0,
    "last_ts": 0,
    "last_analyzed_ts": 0,
}


def get_sim_stats() -> Dict[str, Any]:
    return dict(_SIM)


def add_analyzed(
    symbol: Optional[str] = None,
    tf: Optional[str] = None,
    world: Optional[str] = None,
    ok: Optional[bool] = None,
) -> None:
    # Compat: no rompe imports antiguos.
    _SIM["trades"] = int(_SIM.get("trades", 0)) + 1
    _SIM["last_ts"] = int(time.time())
    _SIM["last_analyzed_ts"] = int(time.time())
