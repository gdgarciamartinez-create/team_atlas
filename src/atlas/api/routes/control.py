from __future__ import annotations

from fastapi import APIRouter

from atlas.runtime import runtime

router = APIRouter(prefix="/control", tags=["control"])


@router.get("")
def get_control() -> dict:
    return {
        "ok": True,
        "control": runtime.get_control_state(),
    }


@router.post("/engine/play")
def engine_play() -> dict:
    control = runtime.set_engine_running(True)
    runtime.log_op("ENGINE_PLAY_HTTP", {"source": "api"})
    return {
        "ok": True,
        "message": "ENGINE RUNNING",
        "control": control,
    }


@router.post("/engine/pause")
def engine_pause() -> dict:
    control = runtime.set_engine_running(False)
    runtime.log_op("ENGINE_PAUSE_HTTP", {"source": "api"})
    return {
        "ok": True,
        "message": "ENGINE PAUSED",
        "control": control,
    }


@router.post("/feed/play")
def feed_play() -> dict:
    control = runtime.set_feed_running(True)
    runtime.log_op("FEED_PLAY_HTTP", {"source": "api"})
    return {
        "ok": True,
        "message": "FEED RUNNING",
        "control": control,
    }


@router.post("/feed/pause")
def feed_pause() -> dict:
    control = runtime.set_feed_running(False)
    runtime.log_op("FEED_PAUSE_HTTP", {"source": "api"})
    return {
        "ok": True,
        "message": "FEED PAUSED",
        "control": control,
    }


@router.post("/feed/reset")
def feed_reset() -> dict:
    control = runtime.reset_feed()
    runtime.log_op("FEED_RESET_HTTP", {"source": "api"})
    return {
        "ok": True,
        "message": "FEED RESET",
        "control": control,
    }