# src/atlas/bot/state.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, Tuple


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class FrozenPlan:
    """
    Plan congelado (WAIT_GATILLO) o señal congelada (SIGNAL).
    No contiene "opiniones", solo datos.
    """
    state: str = "WAIT"  # WAIT | WAIT_GATILLO | SIGNAL
    direction: Optional[str] = None  # "BUY" | "SELL"
    zone_low: Optional[float] = None
    zone_high: Optional[float] = None
    poi: Optional[float] = None  # nivel central (ej. 0.786)
    reason: Optional[str] = None

    # SIGNAL fields (solo cuando state == SIGNAL)
    entry: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    lot: Optional[float] = None

    # Invalidation / bookkeeping
    invalid_above: Optional[float] = None
    invalid_below: Optional[float] = None
    created_at: str = field(default_factory=lambda: _utc_now().isoformat())
    updated_at: str = field(default_factory=lambda: _utc_now().isoformat())
    expires_at: str = field(default_factory=lambda: (_utc_now() + timedelta(minutes=45)).isoformat())

    def touch(self) -> None:
        self.updated_at = _utc_now().isoformat()


class AtlasStateStore:
    """
    Store en memoria para congelar plan/señal entre refresh.
    """
    def __init__(self) -> None:
        self._store: Dict[str, FrozenPlan] = {}

    @staticmethod
    def _key(world: str, symbol: str, tf: str, atlas_mode: Optional[str]) -> str:
        m = atlas_mode or ""
        return f"{world}|{symbol}|{tf}|{m}"

    @staticmethod
    def _is_expired(plan: FrozenPlan) -> bool:
        try:
            exp = datetime.fromisoformat(plan.expires_at)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            return _utc_now() >= exp
        except Exception:
            return False

    def get(self, world: str, symbol: str, tf: str, atlas_mode: Optional[str]) -> Optional[FrozenPlan]:
        k = self._key(world, symbol, tf, atlas_mode)
        plan = self._store.get(k)
        if plan is None:
            return None
        if self._is_expired(plan):
            self._store.pop(k, None)
            return None
        return plan

    def set(self, world: str, symbol: str, tf: str, atlas_mode: Optional[str], plan: FrozenPlan) -> FrozenPlan:
        plan.touch()
        k = self._key(world, symbol, tf, atlas_mode)
        self._store[k] = plan
        return plan

    def clear(self, world: str, symbol: str, tf: str, atlas_mode: Optional[str]) -> None:
        k = self._key(world, symbol, tf, atlas_mode)
        self._store.pop(k, None)


# Singleton global (sirve para uvicorn reload también mientras vive el proceso)
ATLAS_STORE = AtlasStateStore()