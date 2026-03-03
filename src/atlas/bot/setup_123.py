# src/atlas/bot/setup_123.py
# LAB: Setup 1-2-3 con validación obligatoria Fibonacci 0.786–0.79
# NO ejecuta trades. Solo reporta estado al snapshot único.

from typing import Dict, List, Any, Optional

TARGET_MIN = 0.786
TARGET_MAX = 0.79

def _f(x, default=None):
    try:
        return float(x)
    except Exception:
        return default

def _swing(candles: List[Dict[str, Any]], lookback: int) -> Optional[Dict[str, float]]:
    if not candles or len(candles) < max(lookback, 20):
        return None
    r = candles[-lookback:]
    highs = [_f(c.get("high")) for c in r]
    lows  = [_f(c.get("low")) for c in r]
    if any(v is None for v in highs) or any(v is None for v in lows):
        return None
    hi = max(highs)
    lo = min(lows)
    if hi <= lo:
        return None
    return {"hi": hi, "lo": lo}

def _direction(candles: List[Dict[str, Any]]) -> Optional[str]:
    # Dirección simple: close actual vs close 40 velas atrás
    if not candles or len(candles) < 60:
        return None
    a = _f(candles[-40].get("close"))
    b = _f(candles[-1].get("close"))
    if a is None or b is None:
        return None
    if b > a:
        return "long"
    if b < a:
        return "short"
    return None

def _fib_level(direction: str, lo: float, hi: float, corr_price: float) -> Optional[float]:
    rng = hi - lo
    if rng <= 0:
        return None
    if direction == "long":
        return (hi - corr_price) / rng
    if direction == "short":
        return (corr_price - lo) / rng
    return None

def detect_setup_123(symbol: str, candles: List[Dict[str, Any]], armed: bool, lookback: int = 120) -> Dict[str, Any]:
    """
    Devuelve estado del setup 1-2-3:
      - NO_SETUP
      - FORMING (hay idea pero fib no cumple 0.786–0.79)
      - WAIT_P3 (fib OK, esperando confirmación)
      - READY (fib OK + confirmación)
    """
    out = {
        "active": False,
        "symbol": symbol,
        "direction": None,
        "status": "NO_SETUP",
        "armed_gate": bool(armed),
        "p1": None,
        "p2": None,
        "p3": None,
        "fibo": {"valid": False, "level": None, "target_min": TARGET_MIN, "target_max": TARGET_MAX},
        "reason": "NOT_ENOUGH_DATA",
        "confidence": 0.0,
    }

    if not candles or len(candles) < 160:
        return out

    direction = _direction(candles)
    if direction is None:
        out["reason"] = "UNCLEAR_DIRECTION"
        return out

    sw = _swing(candles, lookback=lookback)
    if sw is None:
        out["reason"] = "NO_SWING"
        return out

    hi, lo = sw["hi"], sw["lo"]
    p1 = hi if direction == "long" else lo

    recent = candles[-30:]
    highs = [_f(c.get("high")) for c in recent]
    lows  = [_f(c.get("low")) for c in recent]
    closes = [_f(c.get("close")) for c in recent]
    if any(v is None for v in highs + lows + closes):
        out["reason"] = "BAD_CANDLES"
        return out

    p2 = min(lows) if direction == "long" else max(highs)

    level = _fib_level(direction, lo, hi, p2)
    if level is None:
        out["reason"] = "FIB_FAIL"
        return out

    fib_ok = (TARGET_MIN <= level <= TARGET_MAX)

    last_close = closes[-1]
    last10 = closes[-10:]
    if direction == "long":
        confirm = last_close > max(last10[:-1])
    else:
        confirm = last_close < min(last10[:-1])

    out["active"] = True
    out["direction"] = direction
    out["p1"] = round(p1, 5)
    out["p2"] = round(p2, 5)
    out["fibo"]["level"] = round(level, 5)
    out["fibo"]["valid"] = bool(fib_ok)

    if not fib_ok:
        out["status"] = "FORMING"
        out["reason"] = "FIB_NOT_0_786_0_79"
        out["confidence"] = 0.25
        return out

    out["status"] = "WAIT_P3"
    out["reason"] = "FIB_OK_WAIT_CONFIRM"
    out["confidence"] = 0.6

    if confirm:
        last10_h = [_f(c.get("high")) for c in candles[-10:]]
        last10_l = [_f(c.get("low")) for c in candles[-10:]]
        if not any(v is None for v in last10_h + last10_l):
            p3 = max(last10_h) if direction == "long" else min(last10_l)
            out["p3"] = round(p3, 5)
        out["status"] = "READY"
        out["reason"] = "READY_FIB_0_786_0_79_AND_CONFIRM"
        out["confidence"] = 0.85

    return out