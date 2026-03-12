from __future__ import annotations

from typing import Any, Dict, Tuple

# store en memoria (después lo podemos persistir si querés)
_state: Dict[Tuple[str, str], Dict[str, Any]] = {}


def _has_plan(a: dict) -> bool:
    # plan mínimo: zona o idea
    return bool(a.get("zone") or a.get("plan") or a.get("idea"))


def _has_trigger(a: dict) -> bool:
    # gatillo mínimo: trigger true o entry/sl presentes
    if a.get("trigger"):
        return True
    return a.get("entry") is not None and a.get("sl") is not None


def update_state(symbol: str, tf: str, analysis: dict, score: int) -> str:
    key = (symbol, tf)
    cur = _state.get(key, {"state": "WAIT"})

    st = str(cur.get("state") or "WAIT").upper()

    # Estado actual
    if st == "WAIT":
        if _has_plan(analysis) and score >= 70:
            # congelamos plan
            cur = {
                "state": "WAIT_GATILLO",
                "plan": analysis.get("plan") or analysis.get("idea") or None,
                "zone": analysis.get("zone"),
                "score": score,
            }
            _state[key] = cur
            return "WAIT_GATILLO"
        return "WAIT"

    if st == "WAIT_GATILLO":
        # si pierde plan, vuelve a WAIT
        if not _has_plan(analysis):
            _state[key] = {"state": "WAIT"}
            return "WAIT"

        # si aparece gatillo -> SIGNAL y congelar números
        if _has_trigger(analysis):
            cur["state"] = "SIGNAL"
            cur["entry"] = analysis.get("entry")
            cur["sl"] = analysis.get("sl")
            cur["tp"] = analysis.get("tp")
            cur["score"] = score
            _state[key] = cur
            return "SIGNAL"

        # mantener congelado (no reescribir plan/zone si ya existe)
        cur["score"] = max(int(cur.get("score") or 0), int(score or 0))
        _state[key] = cur
        return "WAIT_GATILLO"

    if st == "SIGNAL":
        # ya congelado: se queda hasta invalidación simple
        # (luego metemos invalidación por tiempo o “2 cierres fuera” si querés)
        _state[key] = cur
        return "SIGNAL"

    _state[key] = {"state": "WAIT"}
    return "WAIT"