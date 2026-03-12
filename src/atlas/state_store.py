from __future__ import annotations

import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Tuple


def _now_ms() -> int:
    return int(time.time() * 1000)


@dataclass
class FrozenPlan:
    # estado de la máquina
    state: str = "WAIT"  # WAIT | WAIT_GATILLO | SIGNAL

    # identidad
    world: str = "ATLAS_IA"
    atlas_mode: str = "SCALPING"
    symbol: str = "XAUUSDz"
    tf: str = "M5"

    # plan congelado
    bias: Optional[str] = None
    zone: Optional[Dict[str, Any]] = None
    idea: Optional[str] = None

    # ejecución congelada (solo en SIGNAL)
    entry: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    tp1: Optional[float] = None

    # control
    created_ms: int = 0
    updated_ms: int = 0
    invalid_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


# Store global (en memoria del proceso)
_STORE: Dict[Tuple[str, str, str, str], FrozenPlan] = {}


def key(world: str, atlas_mode: str, symbol: str, tf: str) -> Tuple[str, str, str, str]:
    return (world, atlas_mode, symbol, tf)


def get_or_create(world: str, atlas_mode: str, symbol: str, tf: str) -> FrozenPlan:
    k = key(world, atlas_mode, symbol, tf)
    if k not in _STORE:
        now = _now_ms()
        _STORE[k] = FrozenPlan(
            state="WAIT",
            world=world,
            atlas_mode=atlas_mode,
            symbol=symbol,
            tf=tf,
            created_ms=now,
            updated_ms=now,
        )
    return _STORE[k]


def set_wait(world: str, atlas_mode: str, symbol: str, tf: str, reason: Optional[str] = None) -> FrozenPlan:
    p = get_or_create(world, atlas_mode, symbol, tf)
    now = _now_ms()
    p.state = "WAIT"
    p.bias = None
    p.zone = None
    p.idea = None
    p.entry = None
    p.sl = None
    p.tp = None
    p.tp1 = None
    p.invalid_reason = reason
    p.updated_ms = now
    return p


def set_wait_gatillo(
    world: str,
    atlas_mode: str,
    symbol: str,
    tf: str,
    *,
    bias: Optional[str],
    zone: Optional[Dict[str, Any]],
    idea: Optional[str],
) -> FrozenPlan:
    p = get_or_create(world, atlas_mode, symbol, tf)
    now = _now_ms()
    p.state = "WAIT_GATILLO"
    p.bias = bias
    p.zone = zone
    p.idea = idea
    # Importante: no definir entry/sl/tp todavía
    p.entry = None
    p.sl = None
    p.tp = None
    p.tp1 = None
    p.invalid_reason = None
    p.updated_ms = now
    return p


def set_signal(
    world: str,
    atlas_mode: str,
    symbol: str,
    tf: str,
    *,
    entry: float,
    sl: float,
    tp: float,
    tp1: Optional[float] = None,
) -> FrozenPlan:
    p = get_or_create(world, atlas_mode, symbol, tf)
    now = _now_ms()
    p.state = "SIGNAL"
    p.entry = float(entry)
    p.sl = float(sl)
    p.tp = float(tp)
    p.tp1 = float(tp1) if tp1 is not None else None
    p.invalid_reason = None
    p.updated_ms = now
    return p


def snapshot_plan(world: str, atlas_mode: str, symbol: str, tf: str) -> Dict[str, Any]:
    p = get_or_create(world, atlas_mode, symbol, tf)
    return p.to_dict()