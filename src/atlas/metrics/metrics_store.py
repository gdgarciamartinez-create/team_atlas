from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List


def _now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


@dataclass
class SetupMetric:
    symbol: str
    tf: str
    setup_type: str
    entry: float
    sl: float
    tp: float
    result: str
    r_multiple: float
    duration: int
    mfe: float
    mae: float
    session: str
    timestamp: str = field(default_factory=_now)
    world: str = ""
    atlas_mode: str = ""


@dataclass
class MetricsStore:
    max_items: int = 10000
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)
    _items: List[Dict[str, Any]] = field(default_factory=list, init=False, repr=False)

    def record(self, metric: SetupMetric) -> None:
        item = asdict(metric)
        with self._lock:
            self._items.append(item)
            if len(self._items) > self.max_items:
                self._items = self._items[-5000:]

    def get_items(self, limit: int = 500) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit), 5000))
        with self._lock:
            return deepcopy(self._items[-limit:])

    def build_summary(self) -> Dict[str, Any]:
        with self._lock:
            items = list(self._items)

        if not items:
            return {
                "count": 0,
                "setup_quality": 0.0,
                "entry_efficiency": 0.0,
                "avg_move_after_entry": 0.0,
                "false_trigger_rate": 0.0,
                "winrate_por_setup": {},
            }

        false_triggers = [x for x in items if str(x.get("result", "")).upper() in {"SL", "FALSE_TRIGGER"}]
        avg_move = sum(float(x.get("mfe", 0.0)) for x in items) / len(items)
        avg_eff = sum(float(x.get("mfe", 0.0)) - float(x.get("mae", 0.0)) for x in items) / len(items)

        by_setup: Dict[str, List[Dict[str, Any]]] = {}
        for item in items:
            by_setup.setdefault(str(item.get("setup_type", "UNKNOWN")), []).append(item)

        winrate_por_setup: Dict[str, float] = {}
        for setup_type, bucket in by_setup.items():
            setup_wins = [x for x in bucket if float(x.get("r_multiple", 0.0)) > 0]
            winrate_por_setup[setup_type] = round(len(setup_wins) / len(bucket), 4) if bucket else 0.0

        return {
            "count": len(items),
            "setup_quality": round(sum(float(x.get("r_multiple", 0.0)) for x in items) / len(items), 4),
            "entry_efficiency": round(avg_eff, 4),
            "avg_move_after_entry": round(avg_move, 4),
            "false_trigger_rate": round(len(false_triggers) / len(items), 4),
            "winrate_por_setup": winrate_por_setup,
        }


metrics_store = MetricsStore()
