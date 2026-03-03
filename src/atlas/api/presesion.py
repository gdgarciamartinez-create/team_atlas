from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Literal, Dict
import datetime

router = APIRouter(prefix="/presesion", tags=["presesion"])

class PresesionItem(BaseModel):
    symbol: str
    light: Literal["red", "yellow", "green"]
    bias: Literal["buy", "sell", "none"]
    note: str
    updated_at: str

# Estado en memoria
INITIAL_SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD", "XAUUSD", "NAS100"]
board_state: Dict[str, PresesionItem] = {
    s: PresesionItem(
        symbol=s, 
        light="yellow", 
        bias="none", 
        note="Esperando apertura", 
        updated_at=datetime.datetime.now().isoformat()
    ) for s in INITIAL_SYMBOLS
}

@router.get("/board", response_model=List[PresesionItem])
def get_board():
    return list(board_state.values())

@router.post("/update")
def update_item(item: PresesionItem):
    board_state[item.symbol] = item
    return {"status": "ok", "item": item}