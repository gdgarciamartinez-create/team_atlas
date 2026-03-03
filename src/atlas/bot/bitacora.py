from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

BITACORA_FILE = os.path.join(
    os.path.dirname(__file__),
    "bitacora_store.json",
)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _ensure_file() -> None:
    if not os.path.exists(BITACORA_FILE):
        with open(BITACORA_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)


def read_all() -> List[Dict[str, Any]]:
    _ensure_file()
    with open(BITACORA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def read_last() -> Optional[Dict[str, Any]]:
    data = read_all()
    if not data:
        return None
    return data[-1]


def append_bitacora(entry: Dict[str, Any]) -> None:
    _ensure_file()
    data = read_all()

    entry = dict(entry)
    entry["ts"] = _now_ms()

    data.append(entry)

    with open(BITACORA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)