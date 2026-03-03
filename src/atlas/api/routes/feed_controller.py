from fastapi import APIRouter
from atlas.bot.feed_control import feed_control

router = APIRouter()

@router.get("/feed/state")
def feed_state():
    return feed_control.state()

@router.post("/feed/play")
def feed_play():
    feed_control.play()
    return feed_control.state()

@router.post("/feed/pause")
def feed_pause():
    feed_control.pause()
    return feed_control.state()

@router.post("/feed/reset")
def feed_reset():
    feed_control.reset()
    return feed_control.state()
