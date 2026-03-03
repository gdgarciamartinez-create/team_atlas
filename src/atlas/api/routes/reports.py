from __future__ import annotations
from fastapi import APIRouter
from typing import Dict, Any

from atlas.core.journal_xlsx import journal_stats

router = APIRouter()

@router.get("/reports")
def reports() -> Dict[str, Any]:
    # Reporte simple: estado del journal
    return {
        "ok": True,
        "journal": journal_stats(),
        "note": "LAB: Solo seguimiento. No ejecuta trades.",
    }
