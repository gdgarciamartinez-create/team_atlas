from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter

router = APIRouter(tags=["health"])


def _build_status():
    return {
        "ok": True,
        "status": "ok",
        "service": "TEAM_ATLAS",
        "mode": "V1_DIAGNOSTIC",
        "ts": datetime.utcnow().isoformat(),
    }


@router.get("/status")
def status():
    return _build_status()