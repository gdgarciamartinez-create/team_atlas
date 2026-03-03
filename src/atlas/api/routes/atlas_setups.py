from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from atlas.api.routes.state import BOT_STATE

router = APIRouter()

class AtlasSetup(BaseModel):
    symbol: str
    direction: str
    notes: Optional[str] = None

@router.post("/atlas/setups/add")
def add_setup(setup: AtlasSetup):
    setups = BOT_STATE.setdefault("setups", [])
    setups.append(setup.dict())
    BOT_STATE["setups"] = setups
    return {"ok": True, "count": len(setups)}

@router.get("/atlas/setups")
def get_setups():
    return BOT_STATE.get("setups", [])