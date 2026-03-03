from datetime import datetime
from zoneinfo import ZoneInfo

TZ_SCL = ZoneInfo("America/Santiago")

START_HOUR = 7
END_HOUR = 11

def calc_presesion_from_candles(candles, symbol: str, tf: str, ts_ms: int):
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=TZ_SCL)

    in_window = START_HOUR <= dt.hour < END_HOUR

    follow_active = in_window

    return {
        "in_window": in_window,
        "follow_active": follow_active,
        "window": "07:00–11:00 Santiago",
        "time_scl": dt.strftime("%Y-%m-%d %H:%M:%S"),
        "symbol": symbol,
        "tf": tf,
        "ob": "-",
        "imb": "-",
        "fibo": {
            "range": "0.79 solo presesión",
            "level": 0.79,
        },
        "note": (
            "Pantalla informativa PRESESIÓN. "
            "0.79 SOLO válido aquí (OB + IMB)."
        ),
    }
