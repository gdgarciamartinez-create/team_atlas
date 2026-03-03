from fastapi import APIRouter

router = APIRouter()

@router.get("/metrics")
def metrics():
    return {"trades": 0, "wins": 0, "losses": 0, "winrate": 0.0}
