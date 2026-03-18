from fastapi import APIRouter

from atlas.metrics.metrics_store import metrics_store
from atlas.metrics.progress_tracker import build_progress_tracker
from atlas.metrics.setup_ranker import build_setup_ranking

router = APIRouter(prefix="/lab_stats", tags=["lab-stats"])


@router.get("/")
def get_lab_stats():
    items = metrics_store.get_items(limit=5000)
    ranking = build_setup_ranking(items)
    progress = build_progress_tracker(target=100)

    by_symbol = {}
    by_setup_type = {}
    by_session = {}
    by_world = {}

    for item in items:
        by_symbol[item.get("symbol", "")] = by_symbol.get(item.get("symbol", ""), 0) + 1
        by_setup_type[item.get("setup_type", "")] = by_setup_type.get(item.get("setup_type", ""), 0) + 1
        by_session[item.get("session", "")] = by_session.get(item.get("session", ""), 0) + 1
        key = item.get("atlas_mode") or item.get("world") or "UNKNOWN"
        by_world[key] = by_world.get(key, 0) + 1

    return {
        "ok": True,
        "total_closed": len(items),
        "by_world": by_world,
        "by_setup_type": by_setup_type,
        "by_symbol": by_symbol,
        "by_session": by_session,
        "top_ranked": ranking[:10],
        "weakest_setups": ranking[-10:],
        "progress": progress[:50],
    }
