# src/atlas/api/mt5_feed.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import time

try:
    import MetaTrader5 as mt5
except Exception as e:
    mt5 = None
    _MT5_IMPORT_ERR = repr(e)
else:
    _MT5_IMPORT_ERR = None


_TF_MAP = {
    "M1":  mt5.TIMEFRAME_M1 if mt5 else None,
    "M2":  mt5.TIMEFRAME_M2 if mt5 else None,
    "M3":  mt5.TIMEFRAME_M3 if mt5 else None,
    "M4":  mt5.TIMEFRAME_M4 if mt5 else None,
    "M5":  mt5.TIMEFRAME_M5 if mt5 else None,
    "M6":  mt5.TIMEFRAME_M6 if mt5 else None,
    "M10": mt5.TIMEFRAME_M10 if mt5 else None,
    "M12": mt5.TIMEFRAME_M12 if mt5 else None,
    "M15": mt5.TIMEFRAME_M15 if mt5 else None,
    "M20": mt5.TIMEFRAME_M20 if mt5 else None,
    "M30": mt5.TIMEFRAME_M30 if mt5 else None,
    "H1":  mt5.TIMEFRAME_H1 if mt5 else None,
    "H2":  mt5.TIMEFRAME_H2 if mt5 else None,
    "H3":  mt5.TIMEFRAME_H3 if mt5 else None,
    "H4":  mt5.TIMEFRAME_H4 if mt5 else None,
    "D1":  mt5.TIMEFRAME_D1 if mt5 else None,
    "W1":  mt5.TIMEFRAME_W1 if mt5 else None,
    "MN1": mt5.TIMEFRAME_MN1 if mt5 else None,
}


def _now_ms() -> int:
    return int(time.time() * 1000)


def _mt5_last_error() -> Tuple[int, str]:
    if not mt5:
        return (-999, "MetaTrader5 import failed")
    try:
        code, msg = mt5.last_error()
        return (int(code), str(msg))
    except Exception as e:
        return (-998, f"last_error exception: {e!r}")


def _ensure_mt5_initialized() -> Tuple[bool, str]:
    if not mt5:
        return False, f"MetaTrader5 not available: {_MT5_IMPORT_ERR}"
    try:
        if mt5.initialize():
            return True, "ok"
        code, msg = _mt5_last_error()
        return False, f"mt5.initialize() failed: [{code}] {msg}"
    except Exception as e:
        return False, f"mt5.initialize() exception: {e!r}"


def _select_symbol(symbol: str) -> Tuple[bool, str]:
    # IMPORTANT: aunque el símbolo “exista”, si no está seleccionado, MT5 puede devolver vacío.
    try:
        info = mt5.symbol_info(symbol)
        if info is None:
            return False, f"symbol_info None for '{symbol}'"
        if not info.visible:
            if not mt5.symbol_select(symbol, True):
                code, msg = _mt5_last_error()
                return False, f"symbol_select failed for '{symbol}': [{code}] {msg}"
        return True, "ok"
    except Exception as e:
        return False, f"_select_symbol exception: {e!r}"


def _rates_to_candles(rates) -> List[Dict[str, Any]]:
    """
    rates es típicamente un numpy.ndarray de dtype con campos:
    time, open, high, low, close, tick_volume, spread, real_volume
    Cada fila suele ser numpy.void, NO tiene .get()
    """
    out: List[Dict[str, Any]] = []
    for r in rates:
        # Acceso por nombre de campo (no .get)
        t_sec = int(r["time"])
        out.append({
            "t": t_sec * 1000,
            "o": float(r["open"]),
            "h": float(r["high"]),
            "l": float(r["low"]),
            "c": float(r["close"]),
            "v": float(r["tick_volume"]) if "tick_volume" in r.dtype.names else float(r["real_volume"]) if "real_volume" in r.dtype.names else 0.0,
        })
    return out


def get_candles_payload(*, world: str, symbol: str, tf: str, count: int = 220) -> Dict[str, Any]:
    """
    Fuente ÚNICA de velas para snapshot_core.
    Siempre devuelve un payload estable: ok/source/world/symbol/tf/ts_ms/candles/error(optional)
    """
    ts_ms = _now_ms()
    w = (world or "").strip()
    s = (symbol or "").strip()
    t = (tf or "").strip().upper()
    n = int(count or 220)

    payload: Dict[str, Any] = {
        "ok": True,
        "source": "mt5",
        "world": w,
        "symbol": s,
        "tf": t,
        "ts_ms": ts_ms,
        "candles": [],
    }

    ok, msg = _ensure_mt5_initialized()
    if not ok:
        payload["ok"] = True
        payload["source"] = "mt5_error_fallback"
        payload["error"] = msg
        return payload

    # Terminal/Account info útil para diagnóstico
    try:
        term = mt5.terminal_info()
        acc = mt5.account_info()
        payload["mt5"] = {
            "terminal": {"connected": bool(getattr(term, "connected", False))} if term else None,
            "account": {"login": int(getattr(acc, "login", 0))} if acc else None,
        }
    except Exception:
        payload["mt5"] = None

    tf_enum = _TF_MAP.get(t)
    if tf_enum is None:
        payload["source"] = "mt5_error_fallback"
        payload["error"] = f"Unsupported tf '{t}'. Use one of: {sorted([k for k in _TF_MAP.keys() if _TF_MAP[k] is not None])}"
        return payload

    ok, msg = _select_symbol(s)
    if not ok:
        payload["source"] = "mt5_error_fallback"
        payload["error"] = msg
        return payload

    try:
        rates = mt5.copy_rates_from_pos(s, tf_enum, 0, n)
        if rates is None:
            code, emsg = _mt5_last_error()
            payload["source"] = "mt5_error_fallback"
            payload["error"] = f"copy_rates_from_pos returned None: [{code}] {emsg}"
            return payload

        if len(rates) == 0:
            # Esto es el NO_CANDLES real.
            payload["candles"] = []
            payload["note"] = "NO_CANDLES"
            return payload

        payload["candles"] = _rates_to_candles(rates)
        return payload

    except Exception as e:
        payload["source"] = "mt5_error_fallback"
        payload["error"] = f"mt5 exception: {e!r}"
        return payload