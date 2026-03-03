# src/atlas/api/routes/alerts.py
from __future__ import annotations
from fastapi import APIRouter, Query
from typing import Dict, Any

from atlas.core.alerts_state import get_alerts_snapshot, clear_alerts, set_world

router = APIRouter()


@router.get("/alerts")
def alerts(limit: int = Query(50)) -> Dict[str, Any]:
    return get_alerts_snapshot(limit=limit)


@router.post("/alerts/clear")
def alerts_clear() -> Dict[str, Any]:
    clear_alerts()
    return {"ok": True}


@router.post("/alerts/world")
def alerts_world(world: str = Query("GENERAL")) -> Dict[str, Any]:
    set_world(world)
    return {"ok": True, "world": world}