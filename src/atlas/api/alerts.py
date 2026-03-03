from fastapi import APIRouter, Query
from atlas.core.alerts_state import get_alerts_snapshot, set_world

router = APIRouter()

@router.get("/alerts")
def alerts_get():
    return {"ok": True, "alerts": get_alerts_snapshot()}

@router.post("/alerts/world")
def alerts_world(world: str = Query(...), enabled: bool = Query(...)):
    set_world(world, enabled)
    return {"ok": True, "alerts": get_alerts_snapshot()}