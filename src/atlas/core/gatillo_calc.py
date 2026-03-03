# src/atlas/core/gatillo_calc.py
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


# Estados del mundo GATILLO (no cambian)
STATE_WAIT = "WAIT"
STATE_WAIT_GATILLO = "WAIT_GATILLO"
STATE_SIGNAL = "SIGNAL"


def _safe_last_candle(candles: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not candles:
        return None
    c = candles[-1]
    # Normalizamos llaves típicas: t,o,h,l,c
    if isinstance(c, dict) and "t" in c:
        return c
    return None


def calc_gatillo_from_candles(
    candles: List[Dict[str, Any]],
    symbol: str,
    tf: str,
    ts_ms: int,
    prev_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Pantalla informativa de GATILLO.
    Regla clave: el plan NO debe variar cada refresh.
    - WAIT: sin plan
    - WAIT_GATILLO: plan congelado (zona/idea fija)
    - SIGNAL: entry/sl/tp definidos (congelados) hasta invalidación

    Este módulo NO decide estrategia avanzada todavía.
    Solo provee estructura estable para que no baile.
    """

    prev_state = prev_state or {}
    prev_mode = str(prev_state.get("state") or STATE_WAIT)

    last = _safe_last_candle(candles)
    last_price = float(last.get("c")) if last else None

    # --- PLAN / PARAMS congelados ---
    frozen = prev_state.get("frozen") or {}

    # Valores mostrados (si no existen, quedan vacíos)
    plan = frozen.get("plan") or {
        "bias": "—",
        "zone": "—",
        "reason": "—",
    }
    levels = frozen.get("levels") or {
        "entry": None,
        "sl": None,
        "tp": None,
    }

    # Lógica mínima (placeholder estable):
    # Si no hay velas -> WAIT
    if not candles:
        return {
            "state": STATE_WAIT,
            "symbol": symbol,
            "tf": tf,
            "ts_ms": ts_ms,
            "last_price": None,
            "plan": {"bias": "—", "zone": "—", "reason": "Sin velas"},
            "levels": {"entry": None, "sl": None, "tp": None},
            "frozen": {},
            "note": "GATILLO es pantalla informativa. Espera velas para habilitar.",
        }

    # Si veníamos con SIGNAL o WAIT_GATILLO, respetamos congelado.
    if prev_mode in (STATE_WAIT_GATILLO, STATE_SIGNAL) and frozen:
        return {
            "state": prev_mode,
            "symbol": symbol,
            "tf": tf,
            "ts_ms": ts_ms,
            "last_price": last_price,
            "plan": plan,
            "levels": levels,
            "frozen": frozen,
            "note": "Plan congelado (no cambia por refresh).",
        }

    # Caso inicial con velas pero sin plan: WAIT
    # (Más adelante acá enchufamos el motor real)
    return {
        "state": STATE_WAIT,
        "symbol": symbol,
        "tf": tf,
        "ts_ms": ts_ms,
        "last_price": last_price,
        "plan": {"bias": "—", "zone": "—", "reason": "Sin plan aún"},
        "levels": {"entry": None, "sl": None, "tp": None},
        "frozen": {},
        "note": "Aún no hay gatillo. Cuando exista plan, pasa a WAIT_GATILLO.",
    }


def freeze_plan(prev_state: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Helper para backend: congelar plan en WAIT_GATILLO.
    """
    frozen = dict(prev_state.get("frozen") or {})
    frozen["plan"] = plan
    frozen.setdefault("levels", {"entry": None, "sl": None, "tp": None})
    return {"state": STATE_WAIT_GATILLO, "frozen": frozen}


def promote_signal(prev_state: Dict[str, Any], levels: Dict[str, Any]) -> Dict[str, Any]:
    """
    Helper para backend: pasar a SIGNAL y congelar entry/sl/tp.
    """
    frozen = dict(prev_state.get("frozen") or {})
    frozen.setdefault("plan", {"bias": "—", "zone": "—", "reason": "—"})
    frozen["levels"] = levels
    return {"state": STATE_SIGNAL, "frozen": frozen}
