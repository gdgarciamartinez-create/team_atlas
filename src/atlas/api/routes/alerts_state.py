from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class AlertsState:
    world_enabled: Dict[str, bool] = field(default_factory=lambda: {
        "GENERAL": False,
        "PRESESION": False,
        "GAP": False,
        "GATILLOS": False,
        "ATLAS_IA": False,
    })

ALERTS = AlertsState()

def get_alerts_snapshot() -> Dict[str, Any]:
    return {"world": ALERTS.world_enabled}

def set_world(world: str, enabled: bool) -> None:
    w = (world or "").strip().upper()
    if w in ALERTS.world_enabled:
        ALERTS.world_enabled[w] = bool(enabled)