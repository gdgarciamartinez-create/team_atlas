from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter

router = APIRouter(tags=["health"])

@router.get("/status")
def api_status():
    return {
        "ok": True,
        "status": "ok",
        "service": "TEAM_ATLAS",
        "mode": "V1_DIAGNOSTIC",
        "ts": datetime.utcnow().isoformat()
    }