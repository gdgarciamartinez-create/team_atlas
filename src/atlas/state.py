# src/atlas/bot/state.py
from __future__ import annotations
from typing import Any, Dict
import time

BOT_STATE: Dict[str, Any] = {
    "phase": "IDLE",  # IDLE | OBSERVANDO | ALERTADO
    "last_decision": "NO_TRADE",  # TRADE | WAIT | NO_TRADE
    "reason_no_trade": "BOOT",
    "last_update_ts": int(time.time()),
    "scenario": {"closed": False, "reason": "", "closed_ts": 0},
    "gap": {"state": "IDLE", "tp_gap": None, "direction": None, "ex_high": None, "ex_low": None},
}


def set_phase(phase: str, last_decision: str, reason_no_trade: str = "") -> None:
    BOT_STATE["phase"] = (phase or "IDLE").strip().upper()
    BOT_STATE["last_decision"] = (last_decision or "NO_TRADE").strip().upper()
    if BOT_STATE["last_decision"] == "NO_TRADE":
        BOT_STATE["reason_no_trade"] = reason_no_trade or "NO_TRADE"
    BOT_STATE["last_update_ts"] = int(time.time())