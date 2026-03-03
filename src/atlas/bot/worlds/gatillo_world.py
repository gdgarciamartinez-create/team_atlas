from __future__ import annotations

from typing import Any, Dict

def build_gatillo_snapshot() -> Dict[str, Any]:
    from atlas.bot.gatillo_engine import gatillo_snapshot  # type: ignore
    return gatillo_snapshot()