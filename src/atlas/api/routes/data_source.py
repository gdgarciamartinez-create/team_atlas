from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from atlas.data.feed_controller import feed_instance

router = APIRouter()

class SourceConfig(BaseModel):
    type: str  # "csv" | "fake"
    path: str = ""
    profile: str = "flat"     # flat | gap_on | window_sweep
    seed: int = 1

@router.post("/atlas/data/source")
def set_source(config: SourceConfig):
    if config.type == "csv":
        if not config.path:
            raise HTTPException(400, "path required for csv")
        feed_instance.set_csv(config.path)
    elif config.type == "fake":
        feed_instance.set_fake(config.profile or "flat", config.seed or 1)
    else:
        raise HTTPException(400, "invalid type")
    return {"ok": True, "status": feed_instance.get_status()}

@router.post("/atlas/data/play")
def play_source():
    feed_instance.play()
    return {"ok": True, "status": feed_instance.get_status()}

@router.post("/atlas/data/pause")
def pause_source():
    feed_instance.pause()
    return {"ok": True, "status": feed_instance.get_status()}

@router.get("/atlas/data/status")
def status_source():
    return feed_instance.get_status()