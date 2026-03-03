from typing import Any, Dict, List, Optional, Tuple

def _last_close(candles: List[Dict[str, Any]]) -> Optional[float]:
    if not candles:
        return None
    return float(candles[-1]["close"])

def analyze_simple(world: str, island: Optional[str], symbol: str, tf: str, candles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    MVP:
    - Verde: TRADE (cuando detectamos “respuesta fuerte” muy simple)
    - Amarillo: WAIT (llegando/observando)
    - Rojo: NO_TRADE
    """

    if not candles or len(candles) < 30:
        return {
            "action": "NO_TRADE",
            "semaforo": "red",
            "reason": "NO_CANDLES",
            "side": None,
        }

    last = candles[-1]
    c = float(last["close"])
    o = float(last["open"])
    h = float(last["high"])
    l = float(last["low"])

    body = abs(c - o)
    rng = max(1e-9, (h - l))

    # heurística simple (después la reemplazamos por tu doctrina completa):
    # vela con cuerpo grande = “movimiento con intención”
    if body / rng > 0.65:
        side = "BUY" if c > o else "SELL"
        return {
            "action": "TRADE",
            "semaforo": "green",
            "reason": "STRONG_BODY",
            "side": side,
        }

    # si no, “observando”
    return {
        "action": "WAIT",
        "semaforo": "yellow",
        "reason": "OBSERVING",
        "side": None,
    }