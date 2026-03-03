from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class MT5Diag:
    ok: bool
    note: str
    last_error: Tuple[int, str] | None
    symbol: str
    tf: str
    requested: int
    returned: int


def _try_import_mt5():
    try:
        import MetaTrader5 as mt5  # type: ignore
        return mt5
    except Exception:
        return None


def _tf_to_mt5_timeframe(tf: str) -> Optional[int]:
    tfu = (tf or "").upper().strip()
    mt5 = _try_import_mt5()
    if mt5 is None:
        return None

    mapping = {
        "M1": mt5.TIMEFRAME_M1,
        "M3": mt5.TIMEFRAME_M3 if hasattr(mt5, "TIMEFRAME_M3") else None,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
    }
    return mapping.get(tfu)


def _normalize_rate_row(r: Any) -> Dict[str, float]:
    # MT5 rate row typically has: time, open, high, low, close
    # We convert to our candle shape: {t, o, h, l, c}
    return {
        "t": int(r["time"]),
        "o": float(r["open"]),
        "h": float(r["high"]),
        "l": float(r["low"]),
        "c": float(r["close"]),
    }


def fetch_candles_mt5(symbol: str, tf: str, n: int = 220) -> Tuple[List[Dict[str, float]], Dict[str, Any]]:
    """
    Lee velas desde MetaTrader5. NUNCA lanza excepción.
    Si MT5 no está disponible / no hay velas / símbolo no existe, devuelve [] + meta diagnóstica.
    """
    sym = (symbol or "").strip()
    tfu = (tf or "").upper().strip()
    n_req = int(n) if n else 0
    n_req = max(1, min(n_req, 5000))

    mt5 = _try_import_mt5()
    if mt5 is None:
        diag = MT5Diag(
            ok=False,
            note="mt5_module_missing",
            last_error=None,
            symbol=sym,
            tf=tfu,
            requested=n_req,
            returned=0,
        )
        return [], {"source": "mt5", "diag": diag.__dict__}

    tf_mt5 = _tf_to_mt5_timeframe(tfu)
    if tf_mt5 is None:
        diag = MT5Diag(
            ok=False,
            note=f"tf_not_supported:{tfu}",
            last_error=None,
            symbol=sym,
            tf=tfu,
            requested=n_req,
            returned=0,
        )
        return [], {"source": "mt5", "diag": diag.__dict__}

    # Initialize (safe to call multiple times)
    try:
        if not mt5.initialize():
            err = mt5.last_error()
            diag = MT5Diag(
                ok=False,
                note="mt5_initialize_failed",
                last_error=(int(err[0]), str(err[1])) if err else None,
                symbol=sym,
                tf=tfu,
                requested=n_req,
                returned=0,
            )
            return [], {"source": "mt5", "diag": diag.__dict__}
    except Exception as e:
        diag = MT5Diag(
            ok=False,
            note=f"mt5_initialize_exception:{type(e).__name__}",
            last_error=None,
            symbol=sym,
            tf=tfu,
            requested=n_req,
            returned=0,
        )
        return [], {"source": "mt5", "diag": diag.__dict__}

    # Ensure symbol exists/selected
    try:
        info = mt5.symbol_info(sym)
        if info is None:
            err = mt5.last_error()
            diag = MT5Diag(
                ok=False,
                note="symbol_not_found",
                last_error=(int(err[0]), str(err[1])) if err else None,
                symbol=sym,
                tf=tfu,
                requested=n_req,
                returned=0,
            )
            return [], {"source": "mt5", "diag": diag.__dict__}

        if not info.visible:
            mt5.symbol_select(sym, True)
    except Exception as e:
        diag = MT5Diag(
            ok=False,
            note=f"symbol_info_exception:{type(e).__name__}",
            last_error=None,
            symbol=sym,
            tf=tfu,
            requested=n_req,
            returned=0,
        )
        return [], {"source": "mt5", "diag": diag.__dict__}

    # Read rates
    try:
        rates = mt5.copy_rates_from_pos(sym, tf_mt5, 0, n_req)
        if rates is None or len(rates) == 0:
            err = mt5.last_error()
            diag = MT5Diag(
                ok=False,
                note="no_candles",
                last_error=(int(err[0]), str(err[1])) if err else None,
                symbol=sym,
                tf=tfu,
                requested=n_req,
                returned=0,
            )
            return [], {"source": "mt5", "diag": diag.__dict__}

        candles = [_normalize_rate_row(r) for r in rates]
        # MT5 returns oldest->newest already; keep it.
        err = mt5.last_error()
        diag = MT5Diag(
            ok=True,
            note="ok",
            last_error=(int(err[0]), str(err[1])) if err else None,
            symbol=sym,
            tf=tfu,
            requested=n_req,
            returned=len(candles),
        )
        return candles, {"source": "mt5", "diag": diag.__dict__}
    except Exception as e:
        err = None
        try:
            err = mt5.last_error()
        except Exception:
            err = None
        diag = MT5Diag(
            ok=False,
            note=f"mt5_copy_rates_exception:{type(e).__name__}",
            last_error=(int(err[0]), str(err[1])) if err else None,
            symbol=sym,
            tf=tfu,
            requested=n_req,
            returned=0,
        )
        return [], {"source": "mt5", "diag": diag.__dict__}


def get_mt5_diag(symbol: str, tf: str, n: int = 50) -> Dict[str, Any]:
    """
    Helper rápido para debug: devuelve SOLO meta (y 0 o pocas velas).
    """
    candles, meta = fetch_candles_mt5(symbol=symbol, tf=tf, n=n)
    meta = dict(meta or {})
    meta["sample_returned"] = len(candles)
    return meta