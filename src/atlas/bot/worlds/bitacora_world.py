from __future__ import annotations

from typing import Any, Dict

def build_bitacora_snapshot() -> Dict[str, Any]:
    from atlas.bot.bitacora_engine import bitacora_snapshot  # type: ignore
    return bitacora_snapshot()