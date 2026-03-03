from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import time


def _to_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _to_int(x: Any, default: int = 0) -> int:
    try:
        if x is None:
            return default
        return int(x)
    except Exception:
        return default


def _normalize_one_candle(row: Any) -> Optional[Dict[str, Any]]:
    """
    Convierte 1 vela que puede venir como:
    - dict
    - numpy.void / record (soporta row['close'], row['time'], etc)
    - objeto con atributos (.open, .high...)
    a un dict estándar {t,o,h,l,c,v}
    """
    if row is None:
        return None

    # 1) dict directo
    if isinstance(row, dict):
        # Acepta variantes comunes
        t = row.get("t", row.get("time", row.get("timestamp", None)))
        o = row.get("o", row.get("open", None))
        h = row.get("h", row.get("high", None))
        l = row.get("l", row.get("low", None))
        c = row.get("c", row.get("close", None))
        v = row.get("v", row.get("tick_volume", row.get("volume", None)))

        if t is None:
            return None

        return {
            "t": _to_int(t),
            "o": _to_float(o),
            "h": _to_float(h),
            "l": _to_float(l),
            "c": _to_float(c),
            "v": _to_float(v),
        }

    # 2) numpy.void / record-like: row["open"] etc
    # Si row no es subscriptable, cae al except y vamos a atributos.
    try:
        # intentamos varias keys típicas
        t = None
        for k in ("t", "time", "timestamp"):
            try:
                if k in row.dtype.names: # numpy record
                    t = row[k]
                    break
            except Exception:
                pass
        if t is None:
            # intento por índice de nombre sin dtype.names
            for k in ("t", "time", "timestamp"):
                try:
                    t = row[k]
                    break
                except Exception:
                    pass

        o = None
        h = None
        l = None
        c = None
        v = None

        for k, out in (("open", "o"), ("high", "h"), ("low", "l"), ("close", "c")):
            try:
                val = row[k]
                if out == "o":
                    o = val
                elif out == "h":
                    h = val
                elif out == "l":
                    l = val
                elif out == "c":
                    c = val
            except Exception:
                pass

        for k in ("tick_volume", "volume", "v"):
            try:
                v = row[k]
                break
            except Exception:
                pass

        if t is None:
            return None

        return {
            "t": _to_int(t),
            "o": _to_float(o),
            "h": _to_float(h),
            "l": _to_float(l),
            "c": _to_float(c),
            "v": _to_float(v),
        }
    except Exception:
        pass

    # 3) atributos (.open, .high...)
    try:
        t = getattr(row, "t", getattr(row, "time", getattr(row, "timestamp", None)))
        if t is None:
            return None
        o = getattr(row, "o", getattr(row, "open", None))
        h = getattr(row, "h", getattr(row, "high", None))
        l = getattr(row, "l", getattr(row, "low", None))
        c = getattr(row, "c", getattr(row, "close", None))
        v = getattr(row, "v", getattr(row, "tick_volume", getattr(row, "volume", None)))

        return {
            "t": _to_int(t),
            "o": _to_float(o),
            "h": _to_float(h),
            "l": _to_float(l),
            "c": _to_float(c),
            "v": _to_float(v),
        }
    except Exception:
        return None


def normalize_candles(raw: Any) -> List[Dict[str, Any]]:
    """
    Devuelve SIEMPRE una lista de velas dicts.
    Si raw viene como dict con key "candles", lo usa.
    Si raw viene como lista/tuple, lo recorre.
    """
    if raw is None:
        return []

    # si viene payload dict
    if isinstance(raw, dict):
        if "candles" in raw:
            raw = raw.get("candles")
        else:
            # si es una vela suelta
            one = _normalize_one_candle(raw)
            return [one] if one else []

    # si es lista/tuple
    if isinstance(raw, (list, tuple)):
        out: List[Dict[str, Any]] = []
        for r in raw:
            one = _normalize_one_candle(r)
            if one:
                # vela inválida si falta low/high por completo: igual la dejamos pero consistente
                if "l" not in one:
                    one["l"] = one["o"]
                if "h" not in one:
                    one["h"] = one["o"]
                out.append(one)
        return out

    # cualquier otro tipo: intento normalizar como 1 vela
    one = _normalize_one_candle(raw)
    return [one] if one else []


def get_candles_payload(
    *,
    world: str,
    symbol: str,
    tf: str,
    count: int = 220,
) -> Dict[str, Any]:
    """
    Esta función es la ÚNICA puerta para velas.
    - Si tenés conector MT5 real, lo llama.
    - Si falla, devuelve fallback controlado.
    """
    ts_ms = int(time.time() * 1000)

    try:
        # Si existe tu conector real, lo importamos acá adentro (para evitar crashes en import-time)
        from atlas.api.routes.mt5_provider import fetch_mt5_candles # <- tu provider real

        raw = fetch_mt5_candles(world=world, symbol=symbol, tf=tf, count=count)
        candles = normalize_candles(raw)

        return {
            "ok": True,
            "source": "mt5",
            "world": world,
            "symbol": symbol,
            "tf": tf,
            "ts_ms": ts_ms,
            "candles": candles,
        }

    except Exception as e:
        # Fallback: nunca romper snapshot por MT5
        return {
            "ok": True,
            "source": "mt5_error_fallback",
            "world": world,
            "symbol": symbol,
            "tf": tf,
            "ts_ms": ts_ms,
            "candles": [],
            "error": f"mt5 error: {e}",
        }