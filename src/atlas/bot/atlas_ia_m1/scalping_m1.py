from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import math
import time

from atlas.bot.worlds.feed import get_feed_with_meta


def _now_ms() -> int:
    return int(time.time() * 1000)


def _f(x: Any) -> Optional[float]:
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except Exception:
        return None


def run_scalping_m1(symbol: str, tf: str, candles: List[Dict[str, Any]], digits: int):
    """
    Lógica simple M1 (tu lógica original).
    Devuelve dict con action WAIT|SIGNAL y niveles.
    """
    if len(candles) < 30:
        return {
            "symbol": symbol,
            "tf": tf,
            "text": "WAIT (historial corto)",
            "action": "WAIT",
            "side": None,
            "entry": None,
            "sl": None,
            "tp": None,
        }

    last = candles[-1]
    prev = candles[-2]

    lc = _f(last.get("c"))
    pc = _f(prev.get("c"))

    if lc is None or pc is None:
        return {
            "symbol": symbol,
            "tf": tf,
            "text": "WAIT (datos incompletos)",
            "action": "WAIT",
            "side": None,
            "entry": None,
            "sl": None,
            "tp": None,
        }

    impulse = lc - pc
    threshold = abs(pc) * 0.0002

    if abs(impulse) > threshold:
        side = "BUY" if impulse > 0 else "SELL"
        entry = round(lc, digits)
        sl = round(pc, digits)
        tp = round(entry + impulse * 2, digits)

        return {
            "symbol": symbol,
            "tf": tf,
            "text": "M1: Micro ruptura activa",
            "action": "SIGNAL",
            "side": side,
            "entry": entry,
            "sl": sl,
            "tp": tp,
        }

    return {
        "symbol": symbol,
        "tf": tf,
        "text": "WAIT (sin micro ruptura)",
        "action": "WAIT",
        "side": None,
        "entry": None,
        "sl": None,
        "tp": None,
    }


def build_snapshot(
    symbol: str = "XAUUSDz",
    tf: str = "M1",
    n: int = 220,
) -> Dict[str, Any]:
    """
    Snapshot estándar para ATLAS_IA (SCALPING_M1).
    - Trae velas del feed fake
    - Corre run_scalping_m1
    - Devuelve contrato con state + (entry/sl/tp) en ROOT cuando es SIGNAL
    """
    candles, meta = get_feed_with_meta(symbol=symbol, tf=tf, n=n)
    meta = meta or {}

    digits = int(meta.get("digits", 2) or 2)
    price = float(meta.get("last_price", 0.0) or 0.0)
    if candles:
        last_c = candles[-1].get("c")
        px = _f(last_c)
        if px is not None:
            price = float(px)

    result = run_scalping_m1(symbol, tf, candles or [], digits)

    state = (result.get("action") or "WAIT").upper()
    side = result.get("side") or "WAIT"

    entry = result.get("entry") or 0.0
    sl = result.get("sl") or 0.0
    tp = result.get("tp") or 0.0

    trade = None
    if state == "SIGNAL" and side in ("BUY", "SELL") and entry and sl and tp:
        trade = {"side": side, "entry": float(entry), "sl": float(sl), "tp": float(tp)}

    return {
        "ok": True,
        "world": "ATLAS_IA",
        "atlas_mode": "SCALPING_M1",
        "symbol": symbol,
        "tf": tf,
        "ts_ms": _now_ms(),
        "candles": candles or [],
        "meta": meta,

        # Estado + precios
        "state": state,
        "side": side if side in ("BUY", "SELL") else "WAIT",
        "price": float(price),

        # ROOT levels (para bitácora)
        "entry": float(entry) if entry else 0.0,
        "sl": float(sl) if sl else 0.0,
        "tp": float(tp) if tp else 0.0,
        "trade": trade,

        "note": result.get("text") or "",

        "analysis": {
            "state": state,
            "side": side,
            "entry": float(entry) if entry else None,
            "sl": float(sl) if sl else None,
            "tp": float(tp) if tp else None,
            "text": result.get("text"),
        },
        "ui": {
            "rows": [
                {"k": "Modo", "v": "SCALPING_M1"},
                {"k": "Estado", "v": state},
                {"k": "Lado", "v": side},
                {"k": "Precio", "v": float(price)},
                {"k": "Entry", "v": float(entry) if entry else ""},
                {"k": "SL", "v": float(sl) if sl else ""},
                {"k": "TP", "v": float(tp) if tp else ""},
                {"k": "Nota", "v": result.get("text") or ""},
            ]
        },
        "last_error": None,
    }