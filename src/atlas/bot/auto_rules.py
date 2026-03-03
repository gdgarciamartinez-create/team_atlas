# src/atlas/bot/auto_rules.py
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

try:
    from zoneinfo import ZoneInfo  # py>=3.9
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore


TZ_NAME_DEFAULT = "America/Santiago"


def _tz():
    """
    Retorna tzinfo (ZoneInfo) o None si zoneinfo no está disponible.
    NO usar tipos inventados tipo ZoneInfoType (Pylance revienta).
    """
    if ZoneInfo is None:
        return None

    tz_name = os.getenv("ATLAS_TZ", TZ_NAME_DEFAULT)
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo(TZ_NAME_DEFAULT)


def now_local() -> datetime:
    tz = _tz()
    if tz is None:
        return datetime.now()
    return datetime.now(tz)


def daily_key() -> str:
    return now_local().strftime("%Y-%m-%d")


def apply_daily_limits(
    *,
    world_real: str,
    daily_count: int,
    daily_cap: int,
) -> Tuple[bool, Optional[str]]:
    """
    Devuelve (allowed, blocked_reason)
    """
    if daily_cap <= 0:
        return True, None
    if daily_count >= daily_cap:
        return False, f"daily_cap_reached:{world_real}"
    return True, None