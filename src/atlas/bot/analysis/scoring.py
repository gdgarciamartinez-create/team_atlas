from __future__ import annotations

from typing import Any, Dict, Optional


def _n(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def calc_rr(entry: float, sl: float, tp: float) -> float:
    risk = abs(_n(entry) - _n(sl))
    reward = abs(_n(tp) - _n(entry))

    if risk <= 0:
        return 0.0

    return reward / risk


def classify_state_from_score(
    score: float,
    *,
    sweep_valid: bool = False,
    timing_ok: bool = True,
    context_ok: bool = True,
    rr: float = 0.0,
    confluence_bonus: int = 0,
) -> str:
    s = _n(score)
    rr = _n(rr)
    confluence_bonus = max(0, min(int(confluence_bonus), 2))

    if s < 7:
        return "SIN_SETUP"

    if s < 9:
        return "SET_UP"

    entry_gate = (
        sweep_valid
        or (rr >= 2.0 and timing_ok and context_ok and confluence_bonus >= 1)
        or (rr >= 2.5 and timing_ok and context_ok)
    )

    if entry_gate:
        return "ENTRY"

    return "SET_UP"


def calc_score(
    *,
    side: str,
    entry: Optional[float],
    sl: Optional[float],
    tp: Optional[float],
    sweep: Dict[str, Any] | None = None,
    context_ok: bool = True,
    timing_ok: bool = True,
    zone_touch_count: int = 1,
    late_entry: bool = False,
    structure_dirty: bool = False,
    spread_bad: bool = False,
    confluence_bonus: int = 0,
) -> Dict[str, Any]:
    """
    Score base:
      contexto alineado        +3
      sweep válido             +2
      llegada/timing bueno     +2
      RR >= 1.5                +1
      RR >= 2.0                +1 extra
      confluencia              +0..+2

    Penaliza:
      entrada tardía           -2
      zona muy manoseada       -1
      estructura sucia         -2
      spread raro              -1
      timing malo              -2
      contexto malo            -3

    Ajuste fino:
      - sweep fuerte pide más calidad
      - 10+ solo sale con estructura realmente buena
    """
    score = 0
    notes = []

    rr = calc_rr(_n(entry), _n(sl), _n(tp))

    if context_ok:
        score += 3
        notes.append("context_ok")
    else:
        score -= 3
        notes.append("context_bad")

    if timing_ok:
        score += 2
        notes.append("timing_ok")
    else:
        score -= 2
        notes.append("timing_bad")

    sw = sweep or {}
    sweep_valid = bool(sw.get("valid"))
    sweep_strength = _n(sw.get("strength"))

    if sweep_valid:
        score += 2
        notes.append("sweep_valid")

        # antes era 0.60, ahora exigimos más
        if sweep_strength >= 0.85:
            score += 1
            notes.append("sweep_strong")

        # ultra fuerte: señal premium
        if sweep_strength >= 1.10:
            score += 1
            notes.append("sweep_ultra")

    if rr >= 1.5:
        score += 1
        notes.append("rr_1_5")

    if rr >= 2.0:
        score += 1
        notes.append("rr_2_0")

    if rr >= 3.0:
        score += 1
        notes.append("rr_3_0")

    if zone_touch_count >= 3:
        score -= 1
        notes.append("zone_overused")

    if late_entry:
        score -= 2
        notes.append("late_entry")

    if structure_dirty:
        score -= 2
        notes.append("dirty_structure")

    if spread_bad:
        score -= 1
        notes.append("spread_bad")

    if confluence_bonus:
        bonus = max(0, min(int(confluence_bonus), 2))
        score += bonus
        notes.append(f"confluence_{bonus}")
    else:
        bonus = 0

    # techo natural
    score = max(0, min(score, 12))

    # 10+ protegido: si no hay base sólida, lo capamos
    premium_gate = (
        sweep_valid and sweep_strength >= 0.85 and timing_ok and context_ok
    ) or (
        rr >= 3.0 and timing_ok and context_ok and bonus >= 1
    )

    if score > 9 and not premium_gate:
        score = 9
        notes.append("capped_to_9")

    state = classify_state_from_score(
        score,
        sweep_valid=sweep_valid,
        timing_ok=timing_ok,
        context_ok=context_ok,
        rr=rr,
        confluence_bonus=bonus,
    )

    return {
        "score": score,
        "state": state,
        "rr": round(rr, 2),
        "notes": notes,
        "side": side,
    }