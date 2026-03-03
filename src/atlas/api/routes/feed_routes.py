from __future__ import annotations

from fastapi import APIRouter

from atlas.bot.worlds.feed import feed_play, feed_pause, feed_reset

router = APIRouter(prefix="/feed", tags=["feed"])


@router.post("/play")
def play():
    feed_play()
    return {"ok": True, "status": "RUNNING"}


@router.post("/pause")
def pause():
    feed_pause()
    return {"ok": True, "status": "PAUSED"}


@router.post("/reset")
def reset():
    feed_reset()
    return {"ok": True, "status": "RESET"}