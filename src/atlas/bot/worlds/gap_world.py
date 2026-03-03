from __future__ import annotations

from typing import Any, Dict

def build_gap_snapshot() -> Dict[str, Any]:
    from atlas.bot.gap_engine import gap_snapshot  # type: ignore
    return gap_snapshot()