# src/atlas/core/market_data.py
from __future__ import annotations

from typing import Any, Dict, List, Optional
import os
import glob

# Intentamos importar MT5, pero el sistema no debe caerse si no está.
try:
    import MetaTrader5 as mt5  # type: ignore
except Exception:
    mt5 = None


def _tf_to_mt5(tf: str):
    """Mapea TF string a TIMEFRAME de MT5."""
    if mt5 is None:
        return None
    tfu = (tf or "").upper().strip()

    # Soportados por ATLAS
    mapping = {
        "M1": mt5.TIMEFRAME_M1,
        "M2": mt5.TIMEFRAME_M2 if hasattr(mt5, "TIMEFRAME_M2") else mt5.TIMEFRAME_M1,
        "M3": mt5.TIMEFRAME_M3 if hasattr(mt5, "TIMEFRAME_M3") else mt5.TIMEFRAME_M1,
        "M4": mt5.TIMEFRAME_M4 if hasattr(mt5, "TIMEFRAME_M4") else mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
    }
    return mapping.get(tfu, mt5.TIMEFRAME_M5)


def _row_to_candle(row: Any) -> Optional[Dict[str, float]]:
    """
    Convierte una fila de MT5 (numpy.void / tuple / dict) a candle ATLAS:
    {t,o,h,l,c,v}
    """
    # Caso dict
    if isinstance(row, dict):
        d = row
    else:
        # numpy.void / record array: tiene .dtype.names y soporta indexación por nombre
        d = None
        names = getattr(getattr(row, "dtype", None), "names", None)
        if names:
            try:
                d = {k: row[k] for k in names}
            except Exception:
                # fallback: list/tuple
                try:
                    vals = list(row)
                    d = {names[i]: vals[i] for i in range(min(len(names), len(vals)))}
                except Exception:
                    d = None
        else:
            # tuple/list
            if isinstance(row, (list, tuple)):
                # MT5 suele traer: (time, open, high, low, close, tick_volume, spread, real_volume)
                if len(row) >= 6:
                    d = {
                        "time": row[0],
                        "open": row[1],
                        "high": row[2],
                        "low": row[3],
                        "close": row[4],
                        "tick_volume": row[5],
                    }

    if not d:
        return None

    # Normalizamos claves típicas MT5
    t = d.get("time")
    o = d.get("open")
    h = d.get("high")
    l = d.get("low")
    c = d.get("close")
    v = d.get("tick_volume", d.get("real_volume", 0))

    if t is None or o is None or h is None or l is None or c is None:
        return None

    # MT5 entrega time en segundos (epoch). ATLAS usa "t" en segundos también.
    try:
        t = int(t)
        o = float(o)
        h = float(h)
        l = float(l)
        c = float(c)
        v = float(v or 0)
    except Exception:
        return None

    return {"t": t, "o": o, "h": h, "l": l, "c": c, "v": v}


def get_candles_mt5(symbol: str, tf: str, count: int = 200) -> List[Dict[str, float]]:
    """
    Devuelve velas desde MT5 ya en formato ATLAS.
    Nunca debe tirar numpy.void.get ni romper.
    """
    if mt5 is None:
        raise RuntimeError("mt5_module_not_available")

    tf_mt5 = _tf_to_mt5(tf)
    if tf_mt5 is None:
        raise RuntimeError("mt5_timeframe_not_available")

    if not mt5.initialize():
        # Si ya está inicializado no pasa nada, pero si falla devolvemos error.
        last = mt5.last_error()
        raise RuntimeError(f"mt5_initialize_failed:{last}")

    # Asegura símbolo
    if not mt5.symbol_select(symbol, True):
        raise RuntimeError(f"mt5_symbol_select_failed:{symbol}")

    rates = mt5.copy_rates_from_pos(symbol, tf_mt5, 0, int(count))
    if rates is None:
        last = mt5.last_error()
        raise RuntimeError(f"mt5_copy_rates_none:{last}")

    out: List[Dict[str, float]] = []
    for r in rates:
        c = _row_to_candle(r)
        if c:
            out.append(c)

    return out


def get_candles_csv(symbol: str, tf: str, count: int = 200) -> List[Dict[str, float]]:
    """
    Fallback CSV: busca archivos en lugares comunes del repo.
    No asume un nombre exacto; hace búsqueda por patrón.
    Formatos soportados (columnas):
    - t,o,h,l,c,v (ideal)
    - time,open,high,low,close,volume
    """
    import csv

    tfu = (tf or "").upper().strip()
    sym = (symbol or "").strip()

    # Patrón de búsqueda flexible
    roots = [
        os.path.join("src", "atlas", "data"),
        os.path.join("src", "atlas", "data", "csv"),
        os.path.join("src", "atlas", "data", "samples"),
        os.path.join("data"),
        os.path.join("data", "csv"),
    ]

    candidates: List[str] = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        # ejemplos posibles: XAUUSDz_M5.csv, XAUUSDz-M5.csv, XAUUSDz.csv, etc.
        patterns = [
            os.path.join(root, f"*{sym}*{tfu}*.csv"),
            os.path.join(root, f"*{sym}*.csv"),
        ]
        for p in patterns:
            candidates.extend(glob.glob(p))

    if not candidates:
        return []

    path = candidates[0]

    out: List[Dict[str, float]] = []
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Probamos ambas familias de headers
            t = row.get("t") or row.get("time")
            o = row.get("o") or row.get("open")
            h = row.get("h") or row.get("high")
            l = row.get("l") or row.get("low")
            c = row.get("c") or row.get("close")
            v = row.get("v") or row.get("volume") or row.get("tick_volume") or "0"

            if not (t and o and h and l and c):
                continue

            try:
                out.append(
                    {
                        "t": int(float(t)),
                        "o": float(o),
                        "h": float(h),
                        "l": float(l),
                        "c": float(c),
                        "v": float(v or 0),
                    }
                )
            except Exception:
                continue

    # Recorta a count desde el final (más reciente)
    if len(out) > int(count):
        out = out[-int(count):]

    return out
