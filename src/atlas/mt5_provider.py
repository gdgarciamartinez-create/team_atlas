# src/atlas/mt5_provider.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


def _safe_import(path: str):
    try:
        mod = __import__(path, fromlist=["*"])
        return mod
    except Exception:
        return None


def _tf_to_mt5(tf: str) -> Optional[int]:
    """
    Mapea TF string -> MetaTrader5.TIMEFRAME_*
    Si MT5 no está, devuelve None.
    """
    mt5 = _safe_import("MetaTrader5")
    if not mt5:
        return None

    tf = (tf or "M1").upper()
    mapping = {
        "M1": getattr(mt5, "TIMEFRAME_M1", None),
        "M2": getattr(mt5, "TIMEFRAME_M2", None),
        "M3": getattr(mt5, "TIMEFRAME_M3", None),
        "M4": getattr(mt5, "TIMEFRAME_M4", None),
        "M5": getattr(mt5, "TIMEFRAME_M5", None),
        "M10": getattr(mt5, "TIMEFRAME_M10", None),
        "M15": getattr(mt5, "TIMEFRAME_M15", None),
        "M30": getattr(mt5, "TIMEFRAME_M30", None),
        "H1": getattr(mt5, "TIMEFRAME_H1", None),
        "H2": getattr(mt5, "TIMEFRAME_H2", None),
        "H4": getattr(mt5, "TIMEFRAME_H4", None),
        "D1": getattr(mt5, "TIMEFRAME_D1", None),
    }
    return mapping.get(tf, getattr(mt5, "TIMEFRAME_M1", None))


def _normalize_candles(rows: Any) -> List[Dict[str, Any]]:
    """
    Normaliza a formato JSON estable:
    {t,o,h,l,c,v}
    - Si viene numpy/structured array de MT5, soporta accesos por clave.
    - Si viene list[dict], lo deja compatible.
    """
    out: List[Dict[str, Any]] = []
    if rows is None:
        return out

    # MT5 suele devolver algo indexable con campos time/open/high/low/close/tick_volume
    try:
        for r in rows:
            if isinstance(r, dict):
                t = r.get("t", r.get("time"))
                o = r.get("o", r.get("open"))
                h = r.get("h", r.get("high"))
                l = r.get("l", r.get("low"))
                c = r.get("c", r.get("close"))
                v = r.get("v", r.get("tick_volume", r.get("volume", 0)))
            else:
                # soporte para structured arrays (MT5)
                t = getattr(r, "time", None) if hasattr(r, "time") else r["time"]
                o = getattr(r, "open", None) if hasattr(r, "open") else r["open"]
                h = getattr(r, "high", None) if hasattr(r, "high") else r["high"]
                l = getattr(r, "low", None) if hasattr(r, "low") else r["low"]
                c = getattr(r, "close", None) if hasattr(r, "close") else r["close"]
                # tick_volume o real_volume
                if hasattr(r, "tick_volume"):
                    v = r.tick_volume
                else:
                    try:
                        v = r["tick_volume"]
                    except Exception:
                        v = 0

            out.append(
                {
                    "t": int(t) * 1000 if t is not None and int(t) < 10_000_000_000 else int(t or 0),
                    "o": float(o or 0),
                    "h": float(h or 0),
                    "l": float(l or 0),
                    "c": float(c or 0),
                    "v": float(v or 0),
                }
            )
    except Exception:
        # Si algo viene raro, devolvemos lista vacía en vez de romper el backend
        return []

    return out


@dataclass
class MT5Provider:
    """
    Provider blindado.
    - Si MT5 está disponible: usa MetaTrader5
    - Si no: intenta fallback a data_source.py (si existe) con get_candles(symbol, tf, count)
    - Si no: devuelve []
    """

    def get_candles(self, symbol: str, tf: str, count: int) -> List[Dict[str, Any]]:
        symbol = str(symbol or "")
        tf = str(tf or "M1").upper()
        count = int(count or 220)

        # 1) Intento MT5
        mt5 = _safe_import("MetaTrader5")
        if mt5:
            try:
                if not mt5.initialize():
                    # si MT5 no inicializa, fallback
                    raise RuntimeError("MT5 initialize failed")
                mt_tf = _tf_to_mt5(tf) or getattr(mt5, "TIMEFRAME_M1", None)
                raw = mt5.copy_rates_from_pos(symbol, mt_tf, 0, count)
                return _normalize_candles(raw)
            except Exception:
                # no rompemos backend
                pass

        # 2) Fallback data_source.py (si existe)
        ds = _safe_import("atlas.data_source")
        if ds:
            try:
                fn = getattr(ds, "get_candles", None)
                if callable(fn):
                    raw = fn(symbol=symbol, tf=tf, count=count)
                    return _normalize_candles(raw)
            except Exception:
                pass

        return []