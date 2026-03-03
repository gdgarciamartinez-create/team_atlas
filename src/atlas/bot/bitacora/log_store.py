# src/atlas/bot/bitacora/log_store.py
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

# Store en memoria (laboratorio). Después lo pasamos a archivo/db si querés.
_LOGS: List[Dict[str, Any]] = []


def _now_iso() -> str:
  return datetime.now().isoformat(timespec="seconds")


def add_log(
  level: str,
  message: str,
  world: Optional[str] = None,
  symbol: Optional[str] = None,
  tf: Optional[str] = None,
  meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
  item = {
    "ts": _now_iso(),
    "level": (level or "INFO").upper().strip(),
    "world": (world or "").strip(),
    "symbol": (symbol or "").strip(),
    "tf": (tf or "").strip(),
    "message": message or "",
    "meta": meta or {},
  }
  _LOGS.append(item)

  # cap para no explotar memoria
  if len(_LOGS) > 2000:
    del _LOGS[:500]

  return item


def get_recent_logs(limit: int = 100) -> List[Dict[str, Any]]:
  lim = max(1, min(int(limit or 100), 500))
  return list(reversed(_LOGS[-lim:]))


def clear_logs() -> None:
  _LOGS.clear()