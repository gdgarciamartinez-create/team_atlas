from fastapi import APIRouter

router = APIRouter(prefix="/feed", tags=["feed"])

FEED_STATE = {"is_playing": False}


@router.post("/play")
def feed_play():
    FEED_STATE["is_playing"] = True
    return {"ok": True, "action": "play", "is_playing": FEED_STATE["is_playing"]}


@router.post("/pause")
def feed_pause():
    FEED_STATE["is_playing"] = False
    return {"ok": True, "action": "pause", "is_playing": FEED_STATE["is_playing"]}


@router.post("/reset")
def feed_reset():
    FEED_STATE["is_playing"] = False
    return {"ok": True, "action": "reset", "is_playing": FEED_STATE["is_playing"]}