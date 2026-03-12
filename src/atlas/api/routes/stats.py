from fastapi import APIRouter

from atlas.runtime import runtime
from atlas.metrics.stats import build_stats

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/")
def get_stats():
    trades = runtime.get_closed_trades(2000)
    stats = build_stats(trades)
    return {
        "ok": True,
        "stats": stats,
    }