from fastapi import APIRouter
from atlas.bot.loop import start_loop, stop_loop
from atlas.bot.state import BOT_STATE
from atlas.bot.logs import push_log

router = APIRouter()

@router.post("/bot/start")
def bot_start():
    start_loop()
    push_log("INFO", "Bot START requested")
    return {"ok": True, "state": BOT_STATE}

@router.post("/bot/stop")
def bot_stop():
    stop_loop()
    push_log("INFO", "Bot STOP requested")
    return {"ok": True, "state": BOT_STATE}
