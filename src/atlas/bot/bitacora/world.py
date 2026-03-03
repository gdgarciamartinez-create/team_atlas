# src/atlas/bot/bitacora/world.py

from __future__ import annotations

from typing import Any, Dict, List
from collections import defaultdict

from atlas.bot.bitacora.store import bitacora_tail


def _build_stats(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    trades = defaultdict(lambda: {"closed": None, "tp1": False})

    for e in events:
        trade_id = e.get("trade_id")
        if not trade_id:
            continue

        ev = e.get("event")

        if ev == "TP1_HIT":
            trades[trade_id]["tp1"] = True

        if ev == "CLOSED":
            reason = e.get("data", {}).get("reason")
            trades[trade_id]["closed"] = reason

    total = 0
    sl = 0
    tp = 0
    be = 0

    for t in trades.values():
        if t["closed"]:
            total += 1
            if t["closed"] == "SL":
                sl += 1
            elif t["closed"] == "TP_FINAL":
                tp += 1
            elif t["closed"] == "BE":
                be += 1

    winrate = round((tp / total) * 100, 2) if total > 0 else 0.0

    return {
        "total_trades_closed": total,
        "sl_count": sl,
        "tp_final_count": tp,
        "be_count": be,
        "winrate_pct": winrate,
    }


def apply_bitacora_world(payload: Dict[str, Any], *, limit: int = 200) -> Dict[str, Any]:
    events = bitacora_tail(limit=limit)
    stats = _build_stats(events)

    out: Dict[str, Any] = dict(payload) if isinstance(payload, dict) else {}
    out["world"] = "BITACORA"

    out["analysis"] = {
        "state": "OK",
        "events_count": len(events),
        "stats": stats,
    }

    out["events"] = events

    out["ui"] = {
        "rows": [
            {
                "trade_id": e.get("trade_id"),
                "event": e.get("event"),
                "ts": e.get("ts"),
            }
            for e in events
        ]
    }

    return out
