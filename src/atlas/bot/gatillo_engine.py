from __future__ import annotations
from typing import Any, Dict, Optional, Tuple, List

def _has_min_candles(candles: List[Dict[str, Any]], n: int) -> bool:
    return isinstance(candles, list) and len(candles) >= n

def _infer_context(candles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Contexto mínimo v1 (seguro):
    - direction: 'bull' o 'bear' por pendiente simple de cierres.
    - valid: True si hay suficiente data y movimiento razonable.
    """
    if not _has_min_candles(candles, 30):
        return {"valid": False, "reason": "Insuficiente data", "direction": None}

    closes = [float(c["close"]) for c in candles[-30:]]
    slope = closes[-1] - closes[0]
    direction = "bull" if slope >= 0 else "bear"

    rng = max(float(c["high"]) for c in candles[-30:]) - min(float(c["low"]) for c in candles[-30:])
    valid = rng > 0

    return {"valid": bool(valid), "reason": None if valid else "Contexto débil", "direction": direction}

def _find_impulse_swing(candles: List[Dict[str, Any]], direction: str) -> Optional[Tuple[float, float]]:
    """
    Impulso v1:
    - bull: low -> high recientes (lookback)
    - bear: high -> low recientes
    """
    if not _has_min_candles(candles, 60):
        return None
    look = candles[-60:]
    highs = [float(c["high"]) for c in look]
    lows  = [float(c["low"]) for c in look]

    hi = max(highs)
    lo = min(lows)
    if abs(hi - lo) <= 0:
        return None

    return (lo, hi) if direction == "bull" else (hi, lo)

def _fib_079(swing: Tuple[float, float], direction: str) -> float:
    """
    0.79 (aprox 0.786–0.79).
    bull: retroceso desde high hacia low.
    bear: retroceso desde low hacia high (equivalente).
    """
    a, b = swing
    if direction == "bull":
        lo, hi = a, b
        return hi - (hi - lo) * 0.79
    else:
        hi, lo = a, b
        return lo + (hi - lo) * 0.79

def _is_clean_arrival(candles: List[Dict[str, Any]]) -> bool:
    """
    Llegada limpia v1: últimas velas sin rangos gigantes.
    """
    last = candles[-10:]
    ranges = [float(c["high"]) - float(c["low"]) for c in last]
    avg = sum(ranges) / len(ranges)
    mx = max(ranges)
    return mx <= avg * 2.0

def _toco_y_me_voy(candles: List[Dict[str, Any]], direction: str) -> Optional[Dict[str, Any]]:
    """
    Gatillo especial:
    - barrido rapidísimo
    - mecha larga
    - rechazo inmediato
    - se aleja en dirección del contexto
    """
    if not _has_min_candles(candles, 5):
        return None

    c = candles[-1]
    o = float(c["open"]); h = float(c["high"]); l = float(c["low"]); cl = float(c["close"])
    rng = max(1e-9, h - l)

    upper_wick = h - max(o, cl)
    lower_wick = min(o, cl) - l
    body = abs(cl - o)

    long_wick = (upper_wick / rng >= 0.55) or (lower_wick / rng >= 0.55)
    small_body = body / rng <= 0.25

    if not (long_wick and small_body):
        return None

    if direction == "bull":
        if lower_wick / rng >= 0.55 and cl >= o:
            return {
                "kind": "toco_y_me_voy",
                "side": "buy",
                "level": l,
                "message": "Toco y me voy: barrido rápido + mecha larga + rechazo inmediato (continuidad)."
            }
    else:
        if upper_wick / rng >= 0.55 and cl <= o:
            return {
                "kind": "toco_y_me_voy",
                "side": "sell",
                "level": h,
                "message": "Toco y me voy: barrido rápido + mecha larga + rechazo inmediato (continuidad)."
            }

    return None

def decide_trigger(state: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Devuelve (trigger, silence_reason).
    Bot cirujano: o avisa o se calla.
    """
    candles = state.get("candles") or []
    presesion_active = bool(state.get("presesion_active", False))

    ctx = _infer_context(candles)
    if not ctx.get("valid"):
        return None, "CONTEXTO_INVALIDO"

    direction = ctx["direction"]

    # FUERA DE PRE-SESIÓN: 0.79 PROHIBIDO
    if not presesion_active:
        tyv = _toco_y_me_voy(candles, direction)
        if tyv:
            return tyv, None
        return None, "SIN_CONFIRMACION"

    # EN PRE-SESIÓN: 0.79 EXCLUSIVO
    swing = _find_impulse_swing(candles, direction)
    if not swing:
        return None, "SIN_CONFIRMACION"

    lvl = _fib_079(swing, direction)

    if not _has_min_candles(candles, 3):
        return None, "SIN_CONFIRMACION"

    prev = candles[-2]
    cur = candles[-1]
    o = float(cur["open"]); h = float(cur["high"]); l = float(cur["low"]); cl = float(cur["close"])

    # tolerancia “toque al pips” v1
    tol = max(0.05, abs(lvl) * 0.00002)

    touched = (abs(l - lvl) <= tol) or (abs(h - lvl) <= tol) or (abs(cl - lvl) <= tol)
    if not touched:
        return None, "SIN_CONFIRMACION"

    clean = _is_clean_arrival(candles)

    # 1) direct_079 (llegada limpia) → toque + cierre a favor
    if clean:
        if direction == "bull" and l <= lvl + tol and cl >= o:
            return {
                "kind": "direct_079",
                "side": "buy",
                "level": float(lvl),
                "message": "0.79 directo: llegada limpia + rechazo a favor."
            }, None
        if direction == "bear" and h >= lvl - tol and cl <= o:
            return {
                "kind": "direct_079",
                "side": "sell",
                "level": float(lvl),
                "message": "0.79 directo: llegada limpia + rechazo a favor."
            }, None

    # 2) sweep_reclaim (llegada agresiva) → cierre vuelve sobre el nivel
    p_cl = float(prev["close"])
    if direction == "bull":
        if p_cl < lvl - tol and cl > lvl + tol:
            return {
                "kind": "sweep_reclaim",
                "side": "buy",
                "level": float(lvl),
                "message": "0.79: barrida + recuperación."
            }, None
    else:
        if p_cl > lvl + tol and cl < lvl - tol:
            return {
                "kind": "sweep_reclaim",
                "side": "sell",
                "level": float(lvl),
                "message": "0.79: barrida + recuperación."
            }, None

    # 3) break_retest: placeholder v1 (silencio por ahora)
    return None, "SIN_CONFIRMACION"
def apply_gatillo_world(payload, symbol: str, tf: str, strategy: str):
    """
    Motor mínimo de mundo GATILLOS / ATLAS_IA
    """
    analysis = {
        "state": "WAIT",
        "message": f"Motor activo ({strategy})",
        "world": strategy,
        "symbol": symbol,
        "tf": tf,
        "gatillo": {
            "estado": "ESPERANDO",
            "direction": "BUY",
            "zone": {"low": 0.0, "high": 0.0},
            "hint": "Sin gatillo aún.",
        },
    }

    payload["analysis"] = analysis
    return payload