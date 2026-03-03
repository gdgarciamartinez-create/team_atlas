from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from atlas.bot.state import BOT_STATE
import uuid

router = APIRouter(prefix="/atlas/setups", tags=["setups"])

class SetupItem(BaseModel):
    id: str = None
    symbol: str
    direction: str
    note: str

@router.get("/", response_model=List[SetupItem])
def list_setups():
    return BOT_STATE.get("setups", [])

@router.post("/add")
def add_setup(item: SetupItem):
    item.id = str(uuid.uuid4())[:8]
    if "setups" not in BOT_STATE:
        BOT_STATE["setups"] = []
    BOT_STATE["setups"].append(item.dict())
    return {"status": "ok", "item": item}