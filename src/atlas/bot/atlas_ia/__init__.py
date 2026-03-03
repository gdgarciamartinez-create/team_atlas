from __future__ import annotations
from typing import Any, Dict

def build_snapshot(*args, **kwargs) -> Dict[str, Any]:
    return {
        "symbol": "",
        "tf": "",
        "analysis": {
            "status": "NO_TRADE",
            "reason": "FOREX_NOT_IMPLEMENTED"
        },
        "ui": {
            "rows": [],
            "meta": {"note": "FOREX snapshot not implemented yet"}
        }
    }