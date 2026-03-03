from __future__ import annotations
from typing import Dict, Any, List, Optional

def reason_pack(code: str, extra: str = "") -> str:
    # Razones cortas, consistentes (para UI + logs)
    if extra:
        return f"{code}:{extra}"
    return code

def need_more_data(candles: List[Dict[str, float]], min_n: int) -> Optional[str]:
    if not candles or len(candles) < min_n:
        return reason_pack("NO_CANDLES", f"min={min_n}")
    return None

def pick_sl_extreme(candles: List[Dict[str, float]], side: str, n: int = 8) -> float:
    chunk = candles[-n:] if len(candles) > n else candles
    if side == "BUY":
        return float(min(c["low"] for c in chunk))
    return float(max(c["high"] for c in chunk))

def rr(entry: float, sl: float, tp: float) -> float:
    risk = abs(entry - sl)
    if risk <= 0:
        return 0.0
    return round(abs(tp - entry) / risk, 2)