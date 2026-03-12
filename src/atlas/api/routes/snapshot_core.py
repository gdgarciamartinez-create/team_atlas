from __future__ import annotations

from typing import Any, Dict, List

from atlas.runtime import runtime
from atlas.trade_manager import trade_manager   
from atlas.bot.atlas_ia.scanner import scan_opportunities
from atlas.api.routes.mt5_provider import get_candles_by_symbol


# -------------------------------------------------------
# helpers
# -------------------------------------------------------

def _normalize_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []

    for r in rows:
        if not isinstance(r, dict):
            continue

        row = dict(r)

        row.setdefault("side", None)
        row.setdefault("entry", None)
        row.setdefault("sl", None)
        row.setdefault("tp", None)
        row.setdefault("parcial", None)
        row.setdefault("lot", None)
        row.setdefault("risk_percent", 0.0)
        row.setdefault("rr", 0.0)

        out.append(row)

    return out


# -------------------------------------------------------
# snapshot main
# -------------------------------------------------------

def build_snapshot(
    world: str,
    atlas_mode: str,
    symbols: List[str],
    tf: str,
    count: int = 220,
) -> Dict[str, Any]:

    # ---------------------------------------------------
    # CANDLES
    # ---------------------------------------------------

    candles_by_symbol = get_candles_by_symbol(
        symbols=symbols,
        tf=tf,
        count=count,
    )

    # ---------------------------------------------------
    # SCAN
    # ---------------------------------------------------

    scan = scan_opportunities(
        atlas_mode=atlas_mode,
        candles_by_symbol=candles_by_symbol,
    )

    rows = scan.get("rows", [])

    rows = _normalize_rows(rows)

    # ---------------------------------------------------
    # FREEZE PLAN
    # ---------------------------------------------------

    frozen_rows: List[Dict[str, Any]] = []

    for row in rows:

        row = runtime.merge_row_with_freeze(row)

        frozen_rows.append(row)

    # ---------------------------------------------------
    # TRADE MANAGER
    # ---------------------------------------------------

    managed_rows = trade_manager.step_rows(runtime, frozen_rows)

    # ---------------------------------------------------
    # SNAPSHOT UI
    # ---------------------------------------------------

    snapshot = {
        "ok": True,
        "world": world,
        "atlas_mode": atlas_mode,
        "tf": tf,
        "count": count,
        "analysis": scan.get("summary", {}),
        "ui": {
            "rows": managed_rows
        },
    }

    return snapshot