from __future__ import annotations

from typing import Any, Dict, List


def _mt5():
    """
    Import protegido de MetaTrader5.
    """
    try:
        import MetaTrader5 as mt5  # type: ignore
        return mt5
    except Exception:
        return None


def _ensure_initialized(mt5) -> Dict[str, Any]:
    """
    Inicializa MT5 si no está listo.
    """
    try:
        if mt5 is None:
            return {"ok": False, "reason": "MT5 import failed", "last_error": [-1, "MT5_IMPORT_FAIL"]}

        if mt5.initialize():
            return {"ok": True, "reason": "initialized", "last_error": mt5.last_error()}

        return {"ok": False, "reason": "initialize() failed", "last_error": mt5.last_error()}
    except Exception as e:
        return {"ok": False, "reason": f"init exception: {e}", "last_error": [-2, "MT5_INIT_EXCEPTION"]}


def _field(r: Any, key: str, default: Any = 0) -> Any:
    """
    Lee un campo de un numpy.void (rates record) de forma segura.
    MT5 devuelve records como numpy.void => acceso r["open"], r["tick_volume"], etc.
    """
    try:
        return r[key]
    except Exception:
        return default


def get_symbols() -> List[str]:
    """
    Lista símbolos disponibles (strings).
    Blindado: si falla, devuelve [].
    """
    mt5 = _mt5()
    st = _ensure_initialized(mt5)
    if not st.get("ok"):
        return []

    try:
        syms = mt5.symbols_get()
        if not syms:
            return []

        out: List[str] = []
        for s in syms:
            name = getattr(s, "name", None)
            if isinstance(name, str) and name.strip():
                out.append(name.strip())
        return out
    except Exception:
        return []


def get_candles(symbol: str, tf: str, count: int = 200) -> Dict[str, Any]:
    """
    Devuelve:
      { ok, candles, digits, last_error, reason }
    candles: [{t,o,h,l,c,v}]
    """
    mt5 = _mt5()
    st = _ensure_initialized(mt5)
    if not st.get("ok"):
        return {
            "ok": False,
            "candles": [],
            "digits": 2,
            "last_error": st.get("last_error"),
            "reason": st.get("reason"),
        }

    tf_map = {
        "M1": mt5.TIMEFRAME_M1,
        "M2": getattr(mt5, "TIMEFRAME_M2", mt5.TIMEFRAME_M1),
        "M3": getattr(mt5, "TIMEFRAME_M3", mt5.TIMEFRAME_M1),
        "M5": mt5.TIMEFRAME_M5,
        "M10": getattr(mt5, "TIMEFRAME_M10", mt5.TIMEFRAME_M5),
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
    }
    timeframe = tf_map.get(str(tf).upper(), mt5.TIMEFRAME_M5)

    try:
        sym = str(symbol).strip()
        if not sym:
            return {"ok": False, "candles": [], "digits": 2, "last_error": mt5.last_error(), "reason": "empty symbol"}

        # clave: seleccionar símbolo (Market Watch)
        try:
            mt5.symbol_select(sym, True)
        except Exception:
            pass

        info = mt5.symbol_info(sym)
        if info is None:
            return {"ok": False, "candles": [], "digits": 2, "last_error": mt5.last_error(), "reason": "symbol_info None"}

        digits = int(getattr(info, "digits", 2) or 2)

        rates = mt5.copy_rates_from_pos(sym, timeframe, 0, int(count or 200))
        if rates is None or len(rates) == 0:
            term = mt5.terminal_info()
            conn = getattr(term, "connected", None) if term else None
            return {
                "ok": False,
                "candles": [],
                "digits": digits,
                "last_error": mt5.last_error(),
                "reason": f"no rates (connected={conn})",
            }

        candles: List[Dict[str, Any]] = []
        for r in rates:
            # numpy.void: acceso por r["campo"]
            t = int(_field(r, "time", 0)) * 1000
            o = float(_field(r, "open", 0.0))
            h = float(_field(r, "high", 0.0))
            l = float(_field(r, "low", 0.0))
            c = float(_field(r, "close", 0.0))

            tv = _field(r, "tick_volume", None)
            rv = _field(r, "real_volume", None)
            vol = tv if tv is not None else (rv if rv is not None else 0.0)

            candles.append({"t": t, "o": o, "h": h, "l": l, "c": c, "v": float(vol)})

        return {"ok": True, "candles": candles, "digits": digits, "last_error": mt5.last_error(), "reason": "OK"}

    except Exception as e:
        return {
            "ok": False,
            "candles": [],
            "digits": 2,
            "last_error": mt5.last_error() if mt5 else [-9, "NO_MT5"],
            "reason": str(e),
        }