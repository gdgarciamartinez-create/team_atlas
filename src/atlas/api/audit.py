from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from atlas.main_state import AUDIT, BOT

router = APIRouter()

@router.get("/audit/tail")
def audit_tail(limit: int = 200):
    return {"events": AUDIT.tail(limit=limit)}

@router.get("/audit/symbol")
def audit_symbol(symbol: str, limit: int = 200):
    return {"events": AUDIT.by_symbol(symbol=symbol, limit=limit)}

@router.get("/audit/event")
def audit_event(event_id: int):
    ev = AUDIT.get_event(event_id)
    return {"event": ev}

class ReplayBody(BaseModel):
    event_id: int

@router.post("/audit/replay")
def replay(body: ReplayBody):
    """
    Replay: devuelve el payload de una evaluación guardada.
    No ejecuta nada, solo re-muestra.
    """
    ev = AUDIT.get_event(body.event_id)
    if not ev:
        return {"ok": False, "error": "NOT_FOUND"}
    return {"ok": True, "replay": ev}

@router.get("/audit/snapshot")
def snapshot_dump():
    # export rápido del snapshot actual
    return {"snapshot": BOT.snapshot()}