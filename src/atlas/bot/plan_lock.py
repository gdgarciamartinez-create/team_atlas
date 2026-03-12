from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


@dataclass
class Plan:
    symbol: str
    tf: str
    atlas_mode: str

    side: str  # BUY | SELL
    zone_low: float
    zone_high: float

    opt_level: float
    band_low: float
    band_high: float
    confidence: float
    n: int

    state: str = "WAIT_GATILLO"  # WAIT_GATILLO | SIGNAL | INVALID
    locked_at: str = ""
    expires_at: str = ""
    reason: str = "PLAN_LOCKED_FIB_OPT"

    # señal definida solo en SIGNAL
    entry: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    trigger_used: Optional[str] = None


# cache en memoria
_PLANS: Dict[str, Plan] = {}


def _key(symbol: str, tf: str, atlas_mode: str) -> str:
    return f"{symbol.upper()}::{tf.upper()}::{atlas_mode.upper()}"


def get_plan(symbol: str, tf: str, atlas_mode: str) -> Optional[Plan]:
    k = _key(symbol, tf, atlas_mode)
    p = _PLANS.get(k)
    if not p:
        return None

    # expiración simple
    try:
        exp = datetime.fromisoformat(p.expires_at.replace("Z", ""))
        if datetime.utcnow() > exp:
            _PLANS.pop(k, None)
            return None
    except Exception:
        # si no podemos parsear, lo dejamos vivir
        pass

    return p


def lock_plan(
    *,
    symbol: str,
    tf: str,
    atlas_mode: str,
    side: str,
    zone_low: float,
    zone_high: float,
    opt_level: float,
    band_low: float,
    band_high: float,
    confidence: float,
    n: int,
    ttl_minutes: int = 60,
    reason: str = "PLAN_LOCKED_FIB_OPT",
) -> Plan:
    now = datetime.utcnow()
    exp = now + timedelta(minutes=max(10, int(ttl_minutes)))

    p = Plan(
        symbol=symbol,
        tf=tf,
        atlas_mode=atlas_mode,
        side=side,
        zone_low=float(zone_low),
        zone_high=float(zone_high),
        opt_level=float(opt_level),
        band_low=float(band_low),
        band_high=float(band_high),
        confidence=float(confidence),
        n=int(n),
        state="WAIT_GATILLO",
        locked_at=now.isoformat() + "Z",
        expires_at=exp.isoformat() + "Z",
        reason=reason,
    )
    _PLANS[_key(symbol, tf, atlas_mode)] = p
    return p


def set_signal(
    *,
    symbol: str,
    tf: str,
    atlas_mode: str,
    entry: float,
    sl: float,
    tp: float,
    trigger_used: str,
) -> Optional[Plan]:
    p = get_plan(symbol, tf, atlas_mode)
    if not p:
        return None
    p.state = "SIGNAL"
    p.entry = float(entry)
    p.sl = float(sl)
    p.tp = float(tp)
    p.trigger_used = str(trigger_used)
    _PLANS[_key(symbol, tf, atlas_mode)] = p
    return p


def invalidate_plan(symbol: str, tf: str, atlas_mode: str, reason: str = "INVALIDATED") -> None:
    k = _key(symbol, tf, atlas_mode)
    p = _PLANS.get(k)
    if not p:
        return
    p.state = "INVALID"
    p.reason = reason
    _PLANS.pop(k, None)


def plan_to_dict(p: Plan) -> Dict[str, Any]:
    return asdict(p)