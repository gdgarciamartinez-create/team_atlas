from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from atlas.metrics.metrics_store import metrics_store
from atlas.metrics.setup_ranker import build_setup_ranking


TZ_SCL = ZoneInfo("America/Santiago")


def classify_session(dt: Optional[datetime] = None) -> str:
    now = dt or datetime.now(TZ_SCL)
    hh = now.hour

    if 0 <= hh < 6:
        return "ASIA"
    if 6 <= hh < 9:
        return "LONDON"
    if 9 <= hh < 12:
        return "NY_OPEN"
    if 12 <= hh < 16:
        return "NY_MID"
    return "LATE"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _match_rank(
    ranking: List[Dict[str, Any]],
    symbol: str,
    tf: str,
    session: str,
    setup_type: str,
    world_or_mode: str,
) -> Optional[Dict[str, Any]]:
    symbol_u = str(symbol or "").strip().upper()
    tf_u = str(tf or "").strip().upper()
    session_u = str(session or "").strip().upper()
    setup_u = str(setup_type or "").strip().upper()
    mode_u = str(world_or_mode or "").strip().upper()

    exact = [
        item
        for item in ranking
        if str(item.get("symbol", "")).strip().upper() == symbol_u
        and str(item.get("tf", "")).strip().upper() == tf_u
        and str(item.get("session", "")).strip().upper() == session_u
        and str(item.get("setup_type", "")).strip().upper() == setup_u
        and str(item.get("world_or_mode", "")).strip().upper() == mode_u
    ]
    if exact:
        exact.sort(key=lambda x: (_safe_float(x.get("rank_score")), int(x.get("samples", 0))), reverse=True)
        return exact[0]

    fallback = [
        item
        for item in ranking
        if str(item.get("symbol", "")).strip().upper() == symbol_u
        and str(item.get("tf", "")).strip().upper() == tf_u
        and str(item.get("setup_type", "")).strip().upper() == setup_u
        and str(item.get("world_or_mode", "")).strip().upper() == mode_u
    ]
    if fallback:
        fallback.sort(key=lambda x: (_safe_float(x.get("rank_score")), int(x.get("samples", 0))), reverse=True)
        return fallback[0]

    return None


def get_adaptive_adjustment(
    symbol: str,
    tf: str,
    setup_type: str,
    world_or_mode: str,
    session: Optional[str] = None,
    ranking: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    current_session = str(session or classify_session()).strip().upper()
    current_ranking = ranking if ranking is not None else build_setup_ranking(metrics_store.get_items())

    match = _match_rank(
        ranking=current_ranking,
        symbol=symbol,
        tf=tf,
        session=current_session,
        setup_type=setup_type,
        world_or_mode=world_or_mode,
    )

    if not match:
        return {
            "score_delta": 0,
            "confidence_boost": 0.0,
            "priority": "NEUTRAL",
            "confidence": "LOW",
            "reason": "No ranking data for this setup",
        }

    rank_score = _safe_float(match.get("rank_score"), 0.0)
    winrate = _safe_float(match.get("winrate"), 0.0)
    avg_r = _safe_float(match.get("avg_r"), 0.0)
    false_rate = _safe_float(match.get("false_trigger_rate"), 0.0)
    entry_eff = _safe_float(match.get("entry_efficiency"), 0.0)
    samples = int(match.get("samples", 0) or 0)
    confidence = str(match.get("confidence", "LOW")).strip().upper()
    priority = str(match.get("priority", "LOW")).strip().upper()

    score_delta = 0
    confidence_boost = 0.0
    reasons: List[str] = []

    if confidence == "LOW" or samples < 10:
        reasons.append("low_confidence_or_low_samples")
    else:
        if rank_score >= 75 and winrate >= 0.55 and avg_r >= 0.50:
            score_delta += 1
            confidence_boost += 0.10
            reasons.append("strong_historical_profile")

        if rank_score >= 90 and false_rate <= 0.15 and entry_eff >= 0.25 and samples >= 40:
            score_delta += 1
            confidence_boost += 0.10
            reasons.append("elite_profile")

        if rank_score <= 45 or false_rate >= 0.35:
            score_delta -= 1
            confidence_boost -= 0.05
            reasons.append("weak_or_false_trigger_prone")

        if rank_score <= 30 and avg_r <= 0.10 and winrate <= 0.40:
            score_delta -= 1
            confidence_boost -= 0.05
            reasons.append("poor_historical_profile")

    if confidence == "MEDIUM":
        confidence_boost *= 0.6
        if score_delta > 1:
            score_delta = 1
        if score_delta < -1:
            score_delta = -1
        reasons.append("medium_confidence_cap")

    score_delta = max(-2, min(2, int(score_delta)))
    confidence_boost = max(-0.20, min(0.20, round(confidence_boost, 2)))

    return {
        "score_delta": score_delta,
        "confidence_boost": confidence_boost,
        "priority": priority,
        "confidence": confidence,
        "reason": ", ".join(reasons) if reasons else "neutral_adjustment",
    }
