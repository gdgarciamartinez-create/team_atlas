from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
def status():
    return {"ok": True, "service": "atlas", "status": "OK"}
