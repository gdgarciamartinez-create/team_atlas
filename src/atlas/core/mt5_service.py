# src/atlas/core/mt5_service.py
from __future__ import annotations

from typing import Any, Dict, List, Optional


def mt5_status() -> Dict[str, Any]:
    """
    Estado MT5 (conectado, cuenta, etc).
    Si no hay MT5 disponible, devolvemos ok=False con error claro.
    """
    try:
        import MetaTrader5 as mt5

        ok = mt5.initialize()
        if not ok:
            return {
                "ok": False,
                "connected": False,
                "last_error": str(mt5.last_error()),
            }

        info = mt5.account_info()
        terminal = mt5.terminal_info()

        return {
            "ok": True,
            "connected": True,
            "account": info._asdict() if info else None,
            "terminal": terminal._asdict() if terminal else None,
            "last_error": None,
        }
    except Exception as e:
        return {"ok": False, "connected": False, "last_error": repr(e)}


def get_candles(symbol: str, tf: str, count: int) -> Dict[str, Any]:
    """
    Velas reales MT5.
    tf ejemplo: M1/M3/M5/M15/H1
    """
    try:
        import MetaTrader5 as mt5

        # Asegura init
        if not mt5.initialize():
            return {
                "ok": False,
                "symbol_resolved": symbol,
                "candles": [],
                "last_error": f"MT5 init failed: {mt5.last_error()}",
            }

        tf_map = {
            "M1": mt5.TIMEFRAME_M1,
            "M2": mt5.TIMEFRAME_M2,
            "M3": mt5.TIMEFRAME_M3,
            "M4": mt5.TIMEFRAME_M4,
            "M5": mt5.TIMEFRAME_M5,
            "M10": mt5.TIMEFRAME_M10,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1,
        }

        timeframe = tf_map.get(tf.upper())
        if timeframe is None:
            return {
                "ok": False,
                "symbol_resolved": symbol,
                "candles": [],
                "last_error": f"TF inválido: {tf}",
            }

        # Selección de símbolo
        resolved = symbol
        if not mt5.symbol_select(resolved, True):
            # fallback por si te mandan sin sufijo z
            if not resolved.endswith("z"):
                alt = resolved + "z"
                if mt5.symbol_select(alt, True):
                    resolved = alt
                else:
                    return {
                        "ok": False,
                        "symbol_resolved": resolved,
                        "candles": [],
                        "last_error": f"No se pudo seleccionar símbolo: {symbol} (ni {alt})",
                    }
            else:
                return {
                    "ok": False,
                    "symbol_resolved": resolved,
                    "candles": [],
                    "last_error": f"No se pudo seleccionar símbolo: {symbol}",
                }

        rates = mt5.copy_rates_from_pos(resolved, timeframe, 0, int(count))
        if rates is None:
            return {
                "ok": False,
                "symbol_resolved": resolved,
                "candles": [],
                "last_error": f"copy_rates_from_pos devolvió None: {mt5.last_error()}",
            }

        candles: List[Dict[str, Any]] = []
        for r in rates:
            candles.append(
                {
                    "time": int(r["time"]),  # unix seconds
                    "open": float(r["open"]),
                    "high": float(r["high"]),
                    "low": float(r["low"]),
                    "close": float(r["close"]),
                    "tick_volume": int(r["tick_volume"]),
                }
            )

        return {
            "ok": True,
            "symbol_resolved": resolved,
            "candles": candles,
            "last_error": None,
        }

    except Exception as e:
        return {
            "ok": False,
            "symbol_resolved": symbol,
            "candles": [],
            "last_error": repr(e),
        }