# src/atlas/bot/gatillo/state.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class TradePlan:
    symbol: str
    tf: str
    side: str  # "BUY" | "SELL"
    zone_low: float
    zone_high: float
    message: str = "Plan congelado en zona"


@dataclass
class TradeSignal:
    entry: float
    sl: float
    tp1: float
    tp_final: float
    rr_planned: float = 2.0


@dataclass
class TradeRuntime:
    trade_id: str
    state: str = "WAIT"  # WAIT|WAIT_GATILLO|SIGNAL|IN_TRADE|CLOSED
    plan: Optional[TradePlan] = None
    signal: Optional[TradeSignal] = None

    running: bool = False

    plan_frozen: bool = False
    signal_frozen: bool = False

    partial_taken: bool = False
    be_set: bool = False
    closed_reason: Optional[str] = None

    # para auditoría básica
    ticks_in_trade: int = 0

    extra: Dict[str, Any] = field(default_factory=dict)
