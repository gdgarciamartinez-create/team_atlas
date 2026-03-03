from __future__ import annotations

from typing import Dict, List
import time
import MetaTrader5 as mt5

from atlas.api.routes.mt5_feed import MT5Feed


# Mapeo string TF → MT5 TF
TF_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
}


def get_candles_payload(*, world: str, symbol: str, tf: str, count: int = 220) -> Dict:

    ts_ms = int(time.time() * 1000)

    try:
        feed = MT5Feed()

        timeframe = TF_MAP.get(tf.upper())
        if timeframe is None:
            return {
                "ok": False,
                "source": "mt5",
                "world": world,
                "symbol": symbol,
                "tf": tf,
                "ts_ms": ts_ms,
                "candles": [],
                "error": "INVALID_TIMEFRAME",
            }

        raw = feed.candles(symbol=symbol, timeframe=timeframe, n=count)

        if not raw:
            return {
                "ok": False,
                "source": "mt5",
                "world": world,
                "symbol": symbol,
                "tf": tf,
                "ts_ms": ts_ms,
                "candles": [],
                "error": "NO_DATA",
            }

        candles: List[Dict] = []

        for r in raw:
            candles.append({
                "t": int(r["time"]) * 1000,
                "o": float(r["open"]),
                "h": float(r["high"]),
                "l": float(r["low"]),
                "c": float(r["close"]),
                "v": 0.0,
            })

        return {
            "ok": True,
            "source": "mt5",
            "world": world,
            "symbol": symbol,
            "tf": tf,
            "ts_ms": candles[-1]["t"],
            "candles": candles,
        }

    except Exception as e:
        return {
            "ok": False,
            "source": "mt5_provider_error",
            "world": world,
            "symbol": symbol,
            "tf": tf,
            "ts_ms": ts_ms,
            "candles": [],
            "error": f"{type(e).__name__}: {e}",
        }