from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Tuple


def _confidence(samples: int, min_samples: int = 20) -> str:
    if samples < min_samples:
        return "LOW"
    if samples < (min_samples * 2):
        return "MEDIUM"
    return "HIGH"


def _priority(rank_score: float) -> str:
    if rank_score >= 75:
        return "HIGH"
    if rank_score >= 55:
        return "MEDIUM"
    return "LOW"


def _rank_score(
    winrate: float,
    avg_r: float,
    false_trigger_rate: float,
    entry_efficiency: float,
    samples: int,
    min_samples: int = 20,
) -> float:
    sample_factor = min(samples / float(min_samples), 1.0)
    raw = (
        (winrate * 45.0)
        + (avg_r * 20.0)
        + (entry_efficiency * 10.0)
        - (false_trigger_rate * 25.0)
    )
    return round(max(raw, 0.0) * sample_factor, 2)


def build_setup_ranking(
    metrics_items: List[Dict[str, Any]],
    min_samples: int = 20,
) -> List[Dict[str, Any]]:
    buckets: Dict[Tuple[str, str, str, str, str], List[Dict[str, Any]]] = defaultdict(list)

    for item in metrics_items:
        key = (
            str(item.get("symbol", "")),
            str(item.get("tf", "")),
            str(item.get("session", "")),
            str(item.get("setup_type", "")),
            str(item.get("world", item.get("atlas_mode", ""))),
        )
        buckets[key].append(item)

    ranking: List[Dict[str, Any]] = []
    for key, bucket in buckets.items():
        symbol, tf, session, setup_type, mode = key
        samples = len(bucket)
        wins = [x for x in bucket if float(x.get("r_multiple", 0.0)) > 0]
        false_triggers = [x for x in bucket if str(x.get("result", "")).upper() in {"SL", "FALSE_TRIGGER"}]

        winrate = len(wins) / samples if samples else 0.0
        avg_r = sum(float(x.get("r_multiple", 0.0)) for x in bucket) / samples if samples else 0.0
        entry_eff = sum(float(x.get("mfe", 0.0)) - float(x.get("mae", 0.0)) for x in bucket) / samples if samples else 0.0
        false_rate = len(false_triggers) / samples if samples else 0.0
        rank_score = _rank_score(winrate, avg_r, false_rate, entry_eff, samples, min_samples=min_samples)

        ranking.append(
            {
                "symbol": symbol,
                "tf": tf,
                "session": session,
                "setup_type": setup_type,
                "world_or_mode": mode,
                "samples": samples,
                "winrate": round(winrate, 4),
                "avg_r": round(avg_r, 4),
                "false_trigger_rate": round(false_rate, 4),
                "entry_efficiency": round(entry_eff, 4),
                "rank_score": rank_score,
                "priority": _priority(rank_score),
                "confidence": _confidence(samples, min_samples=min_samples),
            }
        )

    ranking.sort(key=lambda x: (x["rank_score"], x["samples"]), reverse=True)
    return ranking
