from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from atlas.data.feed_controller import feed_instance

router = APIRouter(prefix="/atlas/data", tags=["data"])

class SourceRequest(BaseModel):
    type: str # csv | fake
    path: str = None
    profile: str = None

@router.post("/source")
def set_source(req: SourceRequest):
    if req.type == "csv":
        ok, msg = feed_instance.set_csv_source(req.path)
    elif req.type == "fake":
        ok, msg = feed_instance.set_fake_source(req.profile or "flat")
    else:
        raise HTTPException(400, "Invalid type")
    
    if not ok:
        raise HTTPException(400, msg)
    return {"status": "ok", "msg": msg}

@router.post("/play")
def play():
    feed_instance.play()
    return {"status": "playing"}

@router.post("/pause")
def pause():
    feed_instance.pause()
    return {"status": "paused"}

@router.get("/status")
def get_status():
    return feed_instance.get_status()