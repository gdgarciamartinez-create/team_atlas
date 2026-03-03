# src/atlas/bot/worlds/group_voice.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def _safe_float(x: Any, default: float = 1e9) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _rank_candidate(snap: Dict[str, Any]) -> Tuple[float, float, float, float]:
    """
    Ranking simple (modo B):
    1) menor distancia normalizada al nivel (dist_norm)
    2) mayor calidad (quality: 0..1) -> usamos negativo para que gane el mayor
    3) mayor rr -> negativo para que gane el mayor
    4) menor edad del gatillo en ms (age_ms)
    """
    a = snap.get("analysis", {}) or {}
    dist_norm = _safe_float(a.get("dist_norm"), default=1e9)
    quality = _safe_float(a.get("quality"), default=0.0)
    rr = _safe_float(a.get("rr"), default=0.0)
    age_ms = _safe_float(a.get("age_ms"), default=1e9)
    return (dist_norm, -quality, -rr, age_ms)


def apply_group_voice(
    group_members: List[Dict[str, Any]],
    group_name: str,
) -> Dict[str, Any]:
    """
    Recibe snapshots ya armados para los símbolos de un grupo.
    Decide quién habla si hay 1+ en estado GATILLO.

    - Si 0 en GATILLO -> nadie ON (todos MUTED o sin voice)
    - Si 1 -> ese ON
    - Si >1 -> desempate por rank y solo 1 ON
    Devuelve:
      {
        "active_symbol": Optional[str],
        "members": List[Dict] (modificados con analysis.voice),
      }
    """
    gatillos = []
    for s in group_members:
        a = s.get("analysis", {}) or {}
        if str(a.get("state", "")).upper() == "GATILLO":
            gatillos.append(s)

    active_symbol: Optional[str] = None

    if len(gatillos) == 1:
        active_symbol = (gatillos[0].get("analysis", {}) or {}).get("symbol")
    elif len(gatillos) > 1:
        gatillos_sorted = sorted(gatillos, key=_rank_candidate)
        active_symbol = (gatillos_sorted[0].get("analysis", {}) or {}).get("symbol")

    # Marcar voice
    for s in group_members:
        a = s.get("analysis", {}) or {}
        sym = a.get("symbol")
        if active_symbol and sym == active_symbol and str(a.get("state", "")).upper() == "GATILLO":
            a["voice"] = "ON"
        else:
            a["voice"] = "MUTED"
        s["analysis"] = a

    return {"active_symbol": active_symbol, "members": group_members, "group": group_name}