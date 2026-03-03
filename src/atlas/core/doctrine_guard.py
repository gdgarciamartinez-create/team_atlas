# src/atlas/core/doctrine_guard.py
from __future__ import annotations
from typing import Any, Optional


class DoctrinalError(Exception):
    pass

SENSITIVE_KEYS = {"entry", "sl", "tp", "zone", "level", "price", "swing", "fibo", "poi"}

def _is_forbidden_float(val: Any) -> bool:
    if isinstance(val, (float, int)):
        return abs(float(val) - 0.79) < 0.0005
    return False


def _recursive_search(data: Any, world: str, current_key: Optional[str] = None) -> None:
    if _is_forbidden_float(data):
        raise DoctrinalError("DOCTRINAL_GUARD_079: Forbidden numeric value 0.79 detected.")
    
    if isinstance(data, str):
        if "0.79" in data or "0.790" in data:
            if (world or "").strip().upper() != "PRESESION":
                raise DoctrinalError("DOCTRINAL_GUARD_079: '0.79' string outside PRESESION.")
            if current_key and current_key.lower() in SENSITIVE_KEYS:
                    raise DoctrinalError(f"DOCTRINAL_GUARD_079: '0.79' string in sensitive key '{current_key}'.")

    if isinstance(data, dict):
        for k, v in data.items():
            _recursive_search(v, world, current_key=str(k))
    elif isinstance(data, list):
        for item in data:
            _recursive_search(item, world, current_key=current_key)


def assert_no_079(payload: dict, world: str) -> None:
    _recursive_search(payload, world)