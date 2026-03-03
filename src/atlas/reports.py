# src/atlas/api/routes/reports.py
from __future__ import annotations
from fastapi import APIRouter
from typing import Dict, Any
import time

router = APIRouter()

@router.get("/reports")
def reports() -> Dict[str, Any]:
    # Stub: evita 404/ruidos. Más adelante metemos reportes reales.
    return {
        "ok": True,
        "ts": int(time.time()),
        "report": {
            "mode": "LAB",
            "note": "Reports stub. No hay reportes reales todavía.",
        },
    }