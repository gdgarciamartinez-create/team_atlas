from fastapi import APIRouter
from pydantic import BaseModel
from atlas.bot.persistence import load_params, save_params
from atlas.bot.state import BOT_STATE

router = APIRouter()

class ParamsPayload(BaseModel):
    symbol: str
    tf: str
    params: dict

@router.get("/params/get")
def get_params(symbol: str, tf: str):
    return load_params(symbol, tf)

@router.post("/params/save")
def save(payload: ParamsPayload):
    save_params(payload.symbol, payload.tf, payload.params)
    if payload.symbol == BOT_STATE["symbol"] and payload.tf == BOT_STATE["tf_exec"]:
        BOT_STATE["params"] = payload.params
    return {"ok": True}