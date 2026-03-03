from fastapi import APIRouter
from atlas.bot.state import BOT_STATE

router = APIRouter(prefix="/control")

@router.post("/play")
def play():
    BOT_STATE["engine"]["running"] = True
    BOT_STATE["bot"] = "running"
    return {"ok": True}

@router.post("/pause")
def pause():
    BOT_STATE["engine"]["running"] = False
    BOT_STATE["bot"] = "paused"
    return {"ok": True}

@router.post("/reset")
def reset():
    BOT_STATE["engine"]["running"] = False
    BOT_STATE["engine"]["tick"] = 0
    BOT_STATE["candles"].clear()
    BOT_STATE["bot"] = "paused"
    return {"ok": True}
