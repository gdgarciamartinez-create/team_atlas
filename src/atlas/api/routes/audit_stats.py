from fastapi import APIRouter

from atlas.runtime import runtime
from atlas.metrics.audit_stats import build_audit_stats

router = APIRouter(prefix="/audit-stats", tags=["audit-stats"])


@router.get("/")
def get_audit_stats():
    trades = runtime.get_closed_trades(2000)
    stats = build_audit_stats(trades)
    return {
        "ok": True,
        "stats": stats,
    }