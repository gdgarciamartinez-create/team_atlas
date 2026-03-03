from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/gap", tags=["gap"])


@router.get("/ping")
def gap_ping():
    return {"ok": True, "module": "gap"}