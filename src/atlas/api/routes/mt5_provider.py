# src/atlas/api/routes/mt5_provider.py
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query

router = APIRouter(prefix="/mt5_provider", tags=["mt5_provider"])


def _tf_to_mt5(tf: str):
    """
    Mapea TF string (M1/M3/M5/M15/M30/H1/H4/D1) a constante MT5.
    """
    tf = (tf or "").upper().strip()

    import MetaTrader5 as mt5  # type: ignore

    mapping = {
        "M1": mt5.TIMEFRAME_M1,
        "M2": mt5.TIMEFRAME_M2,
        "M3": mt5.TIMEFRAME_M3,
        "M4": mt5.TIMEFRAME_M4,
        "M5": mt5.TIMEFRAME_M5,
        "M6": mt5.TIMEFRAME_M6,
        "M10": mt5.TIMEFRAME_M10,
        "M12": mt5.TIMEFRAME_M12,
        "M15": mt5.TIMEFRAME_M15,
        "M20": mt5.TIMEFRAME_M20,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H2": mt5.TIMEFRAME_H2,
        "H3": mt5.TIMEFRAME_H3,
        "H4": mt5.TIMEFRAME_H4,
        "H6": mt5.TIMEFRAME_H6,
        "H8": mt5.TIMEFRAME_H8,
        "H12": mt5.TIMEFRAME_H12,
        "D1": mt5.TIMEFRAME_D1,
        "W1": mt5.TIMEFRAME_W1,
        "MN1": mt5.TIMEFRAME_MN1,
    }
    return mapping.get(tf, mt5.TIMEFRAME_M5)


def _ensure_mt5() -> None:
    """
    Inicializa MT5 si no está inicializado.
    No hace login: asume terminal ya configurada (como venís usando en el proyecto).
    """
    import MetaTrader5 as mt5  # type: ignore

    if mt5.initialize():
        return

    # Si no inicia, dejamos que falle con mensaje claro
    code, msg = mt5.last_error()
    raise RuntimeError(f"MT5 initialize failed: [{code}] {msg}")


def _rates_to_candles(rates) -> List[Dict[str, Any]]:
    """
    Convierte rates de MT5 (numpy structured array) a lista de velas para UI.
    Formato:
      {t: unix_seconds, o: open, h: high, l: low, c: close}
    """
    out: List[Dict[str, Any]] = []
    if rates is None:
        return out

    for r in rates:
        # r["time"] viene en segundos unix
        t = int(r["time"])
        out.append(
            {
                "t": t,
                "o": float(r["open"]),
                "h": float(r["high"]),
                "l": float(r["low"]),
                "c": float(r["close"]),
            }
        )
    return out


def get_candles_payload(
    *,
    world: str,
    symbol: str,
    tf: str,
    count: int = 220,
) -> Dict[str, Any]:
    """
    ✅ FUNCIÓN QUE FALTABA (la que tu shim intenta importar).

    Devuelve:
      {"ok": True, "world":..., "symbol":..., "tf":..., "count":..., "candles":[...]}
    """
    import MetaTrader5 as mt5  # type: ignore

    _ensure_mt5()

    mt5_tf = _tf_to_mt5(tf)

    rates = mt5.copy_rates_from_pos(symbol, mt5_tf, 0, int(count))
    candles = _rates_to_candles(rates)

    return {
        "ok": True,
        "world": world,
        "symbol": symbol,
        "tf": tf,
        "count": int(count),
        "candles": candles,
    }


@router.get("/candles")
def candles_endpoint(
    world: str = Query("ATLAS_IA"),
    symbol: str = Query(...),
    tf: str = Query("M5"),
    count: int = Query(200, ge=50, le=2000),
):
    """
    Endpoint de test directo:
      /api/mt5_provider/candles?symbol=XAUUSDz&tf=M5&count=200
    """
    try:
        return get_candles_payload(world=world, symbol=symbol, tf=tf, count=count)
    except Exception as e:
        return {
            "ok": False,
            "world": world,
            "symbol": symbol,
            "tf": tf,
            "count": int(count),
            "candles": [],
            "error": f"{type(e).__name__}: {e}",
        }