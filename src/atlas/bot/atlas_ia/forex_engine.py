from __future__ import annotations

from typing import Any, Dict, Tuple


def eval_forex(md: Dict[str, Any], raw_query: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    analysis = {
        "world": "ATLAS_IA",
        "atlas_mode": "FOREX",
        "status": "OK",
        "signals": 0,
    }
    ui = {
        "rows": [
            {"k": "world", "v": "ATLAS_IA"},
            {"k": "mode", "v": "FOREX"},
            {"k": "status", "v": "OK"},
        ]
    }
    return analysis, ui
