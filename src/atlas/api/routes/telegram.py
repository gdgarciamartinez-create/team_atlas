from fastapi import APIRouter
from atlas.core.telegram_notify import telegram_enabled, send_telegram

router = APIRouter()

@router.get("/telegram/status")
def tg_status():
    return {"ok": True, "enabled": telegram_enabled()}

@router.post("/telegram/test")
def tg_test():
    ok, msg = send_telegram("TEAM ATLAS: test")
    return {"ok": ok, "msg": msg}