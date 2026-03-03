# src/atlas/bot/risk.py
from __future__ import annotations

from atlas.bot.state import BOT_STATE


def _as_list(x):
    return x if isinstance(x, list) else []


def _atr(candles, n=14):
    candles = _as_list(candles)[-n:]
    if len(candles) < 5:
        return None
    rngs = []
    for c in candles:
        try:
            rngs.append(float(c["high"]) - float(c["low"]))
        except Exception:
            pass
    return (sum(rngs) / len(rngs)) if rngs else None


def build_trade_plan(symbol: str, trigger: dict, structure: dict) -> dict:
    """
    Plan simple laboratorio:
      - entry = trigger.price
      - sl = a 1.2*ATR detrás del swing (aprox)
      - tp1 = entry + 1R (o 0.8R si querés más conservador)
    """
    candles = _as_list(BOT_STATE.get("candles", []))
    last = candles[-1] if candles else None
    price = float(trigger.get("price") or (last["close"] if last else 0.0))

    a = _atr(candles, 14) or max(price * 0.0005, 1.0)  # fallback
    direction = trigger.get("direction", "UP")

    # SL básico por ATR
    if direction == "UP":
        sl = price - (a * 1.2)
        r = price - sl
        tp1 = price + r * 1.0
    else:
        sl = price + (a * 1.2)
        r = sl - price
        tp1 = price - r * 1.0

    # Guardar idea de lotaje por riesgo fijo (solo info)
    mm = BOT_STATE.get("money_management") or {
        "account": 10000,
        "risk_normal": 200, # 2% fijo (SUPERBLOQUE)
        "risk_aggressive": 200,
        "formula": "risk / sl_distance",
    }

    return {
        "symbol": symbol,
        "direction": direction,
        "kind": trigger.get("kind"),
        "entry": round(price, 5),
        "sl": round(sl, 5),
        "tp1": round(tp1, 5),
        "atr": round(a, 5),
        "mm": mm,
        "note": "Gestión Universal: Riesgo 2%. Parcial al +2% (1R). SL a BE.",
    }
