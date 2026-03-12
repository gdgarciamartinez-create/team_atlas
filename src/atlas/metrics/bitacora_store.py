from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List, Optional


def _now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


@dataclass
class BitacoraStore:
    max_ops: int = 5000
    max_closed: int = 5000

    _lock: Lock = field(default_factory=Lock, init=False, repr=False)
    _ops: List[Dict[str, Any]] = field(default_factory=list, init=False, repr=False)
    _closed: List[Dict[str, Any]] = field(default_factory=list, init=False, repr=False)

    # --------------------------------------------------
    # Ops
    # --------------------------------------------------

    def log_op(self, event: str, data: Any) -> None:
        item = {
            "ts": _now(),
            "event": str(event),
            "payload": deepcopy(data),
        }

        with self._lock:
            self._ops.append(item)
            if len(self._ops) > self.max_ops:
                self._ops = self._ops[-2000:]

    def get_ops(self, limit: int = 200) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit), 2000))
        with self._lock:
            return deepcopy(self._ops[-limit:])

    def clear_ops(self) -> None:
        with self._lock:
            self._ops.clear()

    # --------------------------------------------------
    # Closed trades
    # --------------------------------------------------

    def log_closed(self, trade: Dict[str, Any]) -> None:
        item = deepcopy(trade)

        if "ts" not in item or item["ts"] is None:
            item["ts"] = _now()

        with self._lock:
            self._closed.append(item)
            if len(self._closed) > self.max_closed:
                self._closed = self._closed[-2000:]

    def get_closed(self, limit: int = 200) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit), 2000))
        with self._lock:
            return deepcopy(self._closed[-limit:])

    def clear_closed(self) -> None:
        with self._lock:
            self._closed.clear()

    # --------------------------------------------------
    # Utils
    # --------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "ops_count": len(self._ops),
                "closed_count": len(self._closed),
                "last_op": deepcopy(self._ops[-1]) if self._ops else None,
                "last_closed": deepcopy(self._closed[-1]) if self._closed else None,
            }

    def reset(self) -> None:
        with self._lock:
            self._ops.clear()
            self._closed.clear()


bitacora_store = BitacoraStore()
BITACORA = bitacora_store