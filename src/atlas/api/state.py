from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict
import time

@dataclass
class AlertsState:
    enabled: Dict[str, bool] = field(default_factory=dict)
    updated_ts: int = field(default_factory=lambda: int(time.time()))

STATE = AlertsState()

def is_enabled(key: str) -> bool:
    return bool(STATE.enabled.get(key, False))

def set_enabled(key: str, on: bool) -> bool:
    STATE.enabled[key] = bool(on)
    STATE.updated_ts = int(time.time())
    return STATE.enabled[key]

def snapshot_enabled() -> Dict[str, bool]:
    # copia simple
    return dict(STATE.enabled)