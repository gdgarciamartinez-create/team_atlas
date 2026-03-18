from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Tuple

from atlas.metrics.metrics_store import metrics_store


def build_progress_tracker(target: int = 100) -> List[Dict[str, Any]]:
    items = metrics_store.get_items(limit=5000)
    buckets: Dict[Tuple[str, str, str, str], int] = defaultdict(int)

    for item in items:
        key = (
            str(item.get("symbol", "")),
            str(item.get("tf", "")),
            str(item.get("atlas_mode") or item.get("world") or item.get("setup_type", "UNKNOWN")),
            str(item.get("setup_type", "UNKNOWN")),
        )
        buckets[key] += 1

    rows: List[Dict[str, Any]] = []
    for (symbol, tf, world_or_mode, setup_type), count in buckets.items():
        remaining = max(int(target) - count, 0)
        completion = round(count / float(target), 4) if target > 0 else 0.0
        rows.append(
            {
                "symbol": symbol,
                "tf": tf,
                "world_or_mode": world_or_mode,
                "setup_type": setup_type,
                "closed_trades": count,
                "target": int(target),
                "remaining": remaining,
                "completion": completion,
            }
        )

    rows.sort(key=lambda x: (x["completion"], x["closed_trades"]), reverse=True)
    return rows
