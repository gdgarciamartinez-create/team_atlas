# src/atlas/mt5.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


# =========================
# Helpers: safe MT5 import
# =========================

def _import_mt5():
    """
    Importa MetaTrader5 de forma segura.
    Si no está instalado o falla, devolvemos None.
    """
    try:
        import MetaTrader5 as mt5  # type: ignore
        return mt5
    except Exception:
        return None


def _last_error_safe(mt5: Any) -> List[Any]:
    """
    last_error() puede venir como tuple, list o algo raro.
    Además: [1, "Success"] NO es error real (regla del proyecto).
    """
    try:
        le = mt5.last_error()
        if isinstance(le, tuple):
            le = list(le)
        if isinstance(le, list) and len(le) >= 2:
            code = le[0]
            msg = le[1]
            # Regla: [1,"Success"] es OK
            if code == 1 and str(msg).lower() == "success":
                return [0, "ok"]
            return [code, msg]
        return [0, "ok"]
    except Exception:
        return [0, "ok"]


def _obj_to_dict(obj: Any) -> Dict[str, Any]:
    """
    Convierte objetos de MT5 (namedtuple / struct) a dict plano.
    Evita el bug 'numpy.void has no attribute get' porque NO asumimos .get().
    """
    if obj is None:
        return {}

    # Si ya es dict
    if isinstance(obj, dict):
        return obj

    # namedtuple / objects con _asdict
    if hasattr(obj, "_asdict"):
        try:
            return dict(obj._asdict())
        except Exception:
            pass

    # objetos con atributos
    out: Dict[str, Any] = {}
    for k in dir(obj):
        if k.startswith("_"):
            continue
        try:
            v = getattr(obj, k)
        except Exception:
            continue
        # filtramos métodos
        if callable(v):
            continue
        # valores simples
        if isinstance(v, (str, int, float, bool)) or v is None:
            out[k] = v
    return out


def _rates_to_candles(rates: Any) -> List[Dict[str, Any]]:
    """
    rates de mt5.copy_rates_from_pos puede venir como:
    - list/tuple de structs
    - numpy array de dtype (numpy.void)
    Convertimos todo a lista de dict con keys estándar.
    """
    if rates is None:
        return []

    candles: List[Dict[str, Any]] = []

    # Caso: rates es iterable
    try:
        for r in rates:
            # numpy.void soporta acceso por nombres con r['time'] o r['open'] etc
            # pero también puede soportar atributos.
            d: Dict[str, Any] = {}

            # Preferimos indexing por clave si existe
            for key in ("time", "open", "high", "low", "close", "tick_volume"):
                try:
                    d[key] = r[key]  # type: ignore[index]
                    continue
                except Exception:
                    pass
                try:
                    d[key] = getattr(r, key)
                    continue
                except Exception:
                    d[key] = None

            # Normalizamos tipos
            if d["time"] is not None:
                d["time"] = int(d["time"])
            for key in ("open", "high", "low", "close"):
                if d[key] is not None:
                    d[key] = float(d[key])
            if d["tick_volume"] is not None:
                d["tick_volume"] = int(d["tick_volume"])

            # si faltan keys críticas, igual lo guardamos pero con None
            candles.append(d)
    except Exception:
        return []

    return candles


# =========================
# Public API expected by snapshot
# =========================

_TIMEFRAMES = {
    "M1": "TIMEFRAME_M1",
    "M2": "TIMEFRAME_M2",
    "M3": "TIMEFRAME_M3",
    "M4": "TIMEFRAME_M4",
    "M5": "TIMEFRAME_M5",
    "M6": "TIMEFRAME_M6",
    "M10": "TIMEFRAME_M10",
    "M12": "TIMEFRAME_M12",
    "M15": "TIMEFRAME_M15",
    "M20": "TIMEFRAME_M20",
    "M30": "TIMEFRAME_M30",
    "H1": "TIMEFRAME_H1",
    "H2": "TIMEFRAME_H2",
    "H3": "TIMEFRAME_H3",
    "H4": "TIMEFRAME_H4",
    "H6": "TIMEFRAME_H6",
    "H8": "TIMEFRAME_H8",
    "H12": "TIMEFRAME_H12",
    "D1": "TIMEFRAME_D1",
}


def _ensure_initialized(mt5: Any) -> Tuple[bool, List[Any]]:
    """
    Inicializa MT5 si hace falta.
    """
    try:
        # Si ya está inicializado, initialize() suele devolver True igual.
        ok = bool(mt5.initialize())
        le = _last_error_safe(mt5)
        return ok, le
    except Exception:
        return False, [0, "mt5_initialize_failed"]


def get_terminal_info() -> Dict[str, Any]:
    mt5 = _import_mt5()
    if mt5 is None:
        return {
            "ok": False,
            "last_error": [0, "mt5_import_failed"],
            "terminal": None,
            "account": None,
        }

    ok_init, le = _ensure_initialized(mt5)
    if not ok_init:
        return {
            "ok": False,
            "last_error": le,
            "terminal": None,
            "account": None,
        }

    try:
        term = mt5.terminal_info()
        return {
            "ok": True,
            "last_error": _last_error_safe(mt5),
            "terminal": _obj_to_dict(term),
            "account": None,
        }
    except Exception:
        return {
            "ok": False,
            "last_error": _last_error_safe(mt5),
            "terminal": None,
            "account": None,
        }


def get_account_info() -> Dict[str, Any]:
    mt5 = _import_mt5()
    if mt5 is None:
        return {
            "ok": False,
            "last_error": [0, "mt5_import_failed"],
            "terminal": None,
            "account": None,
        }

    ok_init, le = _ensure_initialized(mt5)
    if not ok_init:
        return {
            "ok": False,
            "last_error": le,
            "terminal": None,
            "account": None,
        }

    try:
        acc = mt5.account_info()
        return {
            "ok": True,
            "last_error": _last_error_safe(mt5),
            "terminal": None,
            "account": _obj_to_dict(acc),
        }
    except Exception:
        return {
            "ok": False,
            "last_error": _last_error_safe(mt5),
            "terminal": None,
            "account": None,
        }


def get_candles(symbol: str, tf: str = "M5", count: int = 200) -> Dict[str, Any]:
    """
    Devuelve velas en formato:
    {
      ok: bool,
      last_error: [code, msg],
      candles: [{time, open, high, low, close, tick_volume}, ...]
    }
    """
    mt5 = _import_mt5()
    if mt5 is None:
        return {
            "ok": False,
            "last_error": [0, "mt5_import_failed"],
            "candles": [],
        }

    ok_init, le = _ensure_initialized(mt5)
    if not ok_init:
        return {"ok": False, "last_error": le, "candles": []}

    # timeframe
    tf_key = _TIMEFRAMES.get(tf.upper(), "TIMEFRAME_M5")
    timeframe = getattr(mt5, tf_key, None)
    if timeframe is None:
        timeframe = getattr(mt5, "TIMEFRAME_M5")

    # Si el símbolo no está seleccionado, intentamos seleccionarlo
    try:
        mt5.symbol_select(symbol, True)
    except Exception:
        pass

    try:
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, int(count))
        candles = _rates_to_candles(rates)
        le2 = _last_error_safe(mt5)
        ok = len(candles) > 0
        # Si el mercado está cerrado, puede haber 0 velas nuevas, pero normalmente igual devuelve historia.
        # Si no devuelve nada, reportamos ok False para que lo veas claro.
        return {"ok": ok, "last_error": le2, "candles": candles}
    except Exception:
        return {"ok": False, "last_error": _last_error_safe(mt5), "candles": []}
