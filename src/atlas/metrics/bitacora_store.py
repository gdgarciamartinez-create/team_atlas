from __future__ import annotations

import csv
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional


def _now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


TRADES_CSV_PATH = Path("atlas_trades.csv")


@dataclass
class BitacoraStore:
    max_ops: int = 5000
    max_closed: int = 5000

    _lock: Lock = field(default_factory=Lock, init=False, repr=False)
    _ops: List[Dict[str, Any]] = field(default_factory=list, init=False, repr=False)
    _closed: List[Dict[str, Any]] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        self._load_closed_from_csv()

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

    def _load_closed_from_csv(self) -> None:
        if not TRADES_CSV_PATH.exists():
            return

        loaded: List[Dict[str, Any]] = []

        try:
            with TRADES_CSV_PATH.open("r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not isinstance(row, dict):
                        continue
                    loaded.append(
                        {
                            "time": row.get("time") or row.get("ts"),
                            "ts": row.get("ts"),
                            "world": row.get("world"),
                            "atlas_mode": row.get("atlas_mode"),
                            "mode": row.get("mode") or row.get("atlas_mode"),
                            "symbol": row.get("symbol"),
                            "tf": row.get("tf"),
                            "side": row.get("side"),
                            "score": _to_number(row.get("score")),
                            "state_at_entry": row.get("state_at_entry"),
                            "trade_id": row.get("trade_id"),
                            "parent_trade_id": row.get("parent_trade_id"),
                            "leg_id": _to_number(row.get("leg_id")),
                            "is_partial": _to_bool(row.get("is_partial")),
                            "partial_percent": _to_number(row.get("partial_percent")),
                            "lot": _to_number(row.get("lot")),
                            "lot_raw": _to_number(row.get("lot_raw")),
                            "lot_capped": _to_number(row.get("lot_capped")),
                            "lot_cap_reason": row.get("lot_cap_reason"),
                            "lot_error": row.get("lot_error"),
                            "risk_percent": _to_number(row.get("risk_percent")),
                            "entry_price": _to_number(row.get("entry_price") or row.get("entry")),
                            "tp1_price": _to_number(row.get("tp1_price")),
                            "tp2_price": _to_number(row.get("tp2_price") or row.get("tp")),
                            "sl_price": _to_number(row.get("sl_price") or row.get("sl")),
                            "exit_price": _to_number(row.get("exit_price") or row.get("exit")),
                            "entry": _to_number(row.get("entry")),
                            "sl": _to_number(row.get("sl")),
                            "tp": _to_number(row.get("tp")),
                            "exit": _to_number(row.get("exit")),
                            "close_price": _to_number(row.get("close_price") or row.get("exit")),
                            "exit_reason": row.get("exit_reason"),
                            "result": row.get("result"),
                            "raw_result": row.get("raw_result"),
                            "asset_type": row.get("asset_type"),
                            "price_move": _to_number(row.get("price_move")),
                            "pip_move": _to_number(row.get("pip_move")),
                            "point_move": _to_number(row.get("point_move")),
                            "pips": _to_number(row.get("pips")),
                            "usd_result": _to_number(row.get("usd_result") or row.get("usd")),
                            "usd": _to_number(row.get("usd")),
                            "opened_at": row.get("opened_at") or row.get("entry_ts") or row.get("signal_ts"),
                            "signal_ts": row.get("signal_ts"),
                            "entry_ts": row.get("entry_ts"),
                            "closed_at": row.get("closed_at") or row.get("closed_ts") or row.get("ts"),
                            "closed_ts": row.get("closed_ts") or row.get("ts"),
                            "duration_sec": _to_number(row.get("duration_sec")),
                        }
                    )
        except Exception:
            return

        with self._lock:
            self._closed = loaded[-self.max_closed:]


def _to_number(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except Exception:
        return None


def _to_bool(value: Any) -> Optional[bool]:
    if value in (None, ""):
        return None
    s = str(value).strip().lower()
    if s in {"true", "1", "yes"}:
        return True
    if s in {"false", "0", "no"}:
        return False
    return None


bitacora_store = BitacoraStore()
BITACORA = bitacora_store
