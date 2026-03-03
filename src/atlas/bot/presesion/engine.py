from __future__ import annotations

from typing import Any, Dict, Tuple


def eval_presesion(md: Dict[str, Any], raw_query: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    analysis = {
        "world": "PRESESION",
        "status": "OK",
        "mode": "ALERTA",
    }
    ui = {
        "rows": [
            {"k": "world", "v": "PRESESION"},
            {"k": "status", "v": "OK"},
            {"k": "mode", "v": "ALERTA"},
        ]
    }
    return analysis, ui
