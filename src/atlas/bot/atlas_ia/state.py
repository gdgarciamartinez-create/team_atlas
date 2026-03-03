# src/atlas/bot/atlas_ia/state.py
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Tuple


Key = Tuple[str, str, str]  # (symbol, tf_norm, atlas_mode)


@dataclass
class PlanState:
    plan_id: str
    status: str  # WAIT | WAIT_GATILLO | SIGNAL
    side: Optional[str] = None  # BUY | SELL
    text: str = ""

    # zona congelada (si aplica)
    zone_low: Optional[float] = None
    zone_high: Optional[float] = None

    # precios congelados (solo en SIGNAL)
    entry: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None

    # control de vida
    created_t: int = 0
    last_t: int = 0
    ttl_bars: int = 0  # cuantos “pasos” aguanta el plan

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


_PLANS: Dict[Key, PlanState] = {}


def _mk_plan_id(symbol: str, tf_norm: str, atlas_mode: str, t: int) -> str:
    return f"{symbol}:{tf_norm}:{atlas_mode}:{t}"


def get_plan(symbol: str, tf_norm: str, atlas_mode: str) -> Optional[PlanState]:
    return _PLANS.get((symbol, tf_norm, atlas_mode))


def set_plan(symbol: str, tf_norm: str, atlas_mode: str, plan: PlanState) -> None:
    _PLANS[(symbol, tf_norm, atlas_mode)] = plan


def clear_plan(symbol: str, tf_norm: str, atlas_mode: str) -> None:
    _PLANS.pop((symbol, tf_norm, atlas_mode), None)


def upsert_plan_wait_gatillo(
    *,
    symbol: str,
    tf_norm: str,
    atlas_mode: str,
    t: int,
    side: str,
    text: str,
    zone_low: Optional[float],
    zone_high: Optional[float],
    ttl_bars: int,
) -> PlanState:
    existing = get_plan(symbol, tf_norm, atlas_mode)

    if existing and existing.status in ("WAIT_GATILLO", "SIGNAL"):
        # ya hay plan congelado: solo actualizo last_t para que no muera
        existing.last_t = t
        return existing

    plan = PlanState(
        plan_id=_mk_plan_id(symbol, tf_norm, atlas_mode, t),
        status="WAIT_GATILLO",
        side=side,
        text=text,
        zone_low=zone_low,
        zone_high=zone_high,
        entry=None,
        sl=None,
        tp=None,
        created_t=t,
        last_t=t,
        ttl_bars=int(ttl_bars),
    )
    set_plan(symbol, tf_norm, atlas_mode, plan)
    return plan


def promote_to_signal(
    *,
    symbol: str,
    tf_norm: str,
    atlas_mode: str,
    t: int,
    entry: float,
    sl: float,
    tp: float,
    text: str,
) -> PlanState:
    plan = get_plan(symbol, tf_norm, atlas_mode)
    if not plan:
        # si no había plan, igual creo uno ya en SIGNAL (robusto)
        plan = PlanState(
            plan_id=_mk_plan_id(symbol, tf_norm, atlas_mode, t),
            status="SIGNAL",
            created_t=t,
            last_t=t,
            ttl_bars=999999,
        )
    plan.status = "SIGNAL"
    plan.text = text
    plan.entry = entry
    plan.sl = sl
    plan.tp = tp
    plan.last_t = t
    set_plan(symbol, tf_norm, atlas_mode, plan)
    return plan


def expire_if_needed(
    *,
    symbol: str,
    tf_norm: str,
    atlas_mode: str,
    bars_elapsed: int,
) -> None:
    plan = get_plan(symbol, tf_norm, atlas_mode)
    if not plan:
        return
    if plan.ttl_bars <= 0:
        return
    if bars_elapsed >= plan.ttl_bars and plan.status != "SIGNAL":
        clear_plan(symbol, tf_norm, atlas_mode)
