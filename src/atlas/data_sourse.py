# src/atlas/data_source.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict
import hashlib
import random
import time


TF_SECONDS: Dict[str, int] = {
    "M1": 60,
    "M3": 180,
    "M5": 300,
    "M15": 900,
    "M30": 1800,
    "H1": 3600,
    "H4": 14400,
    "D1": 86400,
}


@dataclass
class Candle:
    t: int
    o: float
    h: float
    l: float
    c: float
    v: int

    def to_dict(self) -> dict:
        return {"t": self.t, "o": self.o, "h": self.h, "l": self.l, "c": self.c, "v": self.v}


def _seed(symbol: str, tf: str) -> int:
    s = f"{symbol}|{tf}".encode("utf-8")
    return int(hashlib.sha256(s).hexdigest()[:8], 16)


def _default_price(symbol: str) -> float:
    # Defaults razonables para ver charts coherentes
    sym = symbol.upper()
    if "XAU" in sym:
        return 4900.0
    if "NAS" in sym or "USTEC" in sym:
        return 21500.0
    if "US30" in sym:
        return 38000.0
    if "EURUSD" in sym:
        return 1.10
    if "GBPUSD" in sym:
        return 1.27
    if "USDJPY" in sym:
        return 150.0
    return 100.0


def fake_get_candles(symbol: str, tf: str, count: int, now_ts: int | None = None) -> List[dict]:
    """
    Generador determinístico (estable) de velas para UI/dev.
    - No depende de MT5.
    - Siempre devuelve 'count' velas si count>0.
    """
    tf = tf.upper()
    sec = TF_SECONDS.get(tf, 60)

    if count <= 0:
        return []

    if now_ts is None:
        now_ts = int(time.time())

    # alineamos a múltiplo del TF para que el tiempo sea prolijo
    end_t = now_ts - (now_ts % sec)
    start_t = end_t - sec * count

    rng = random.Random(_seed(symbol, tf))
    base = _default_price(symbol)

    candles: List[Candle] = []
    price = base

    # volatilidad por activo
    sym = symbol.upper()
    if "XAU" in sym:
        step = 0.8
    elif "NAS" in sym or "USTEC" in sym:
        step = 6.0
    elif "US30" in sym:
        step = 10.0
    else:
        step = 0.0006

    for i in range(count):
        t = start_t + sec * (i + 1)

        # caminata con sesgo suave + ruido
        drift = (rng.random() - 0.5) * step * 0.25
        shock = (rng.random() - 0.5) * step * 1.2
        new_close = price + drift + shock

        o = price
        c = new_close

        # mechas
        wick_up = abs((rng.random() - 0.5) * step * 1.0)
        wick_dn = abs((rng.random() - 0.5) * step * 1.0)

        h = max(o, c) + wick_up
        l = min(o, c) - wick_dn

        v = int(500 + rng.random() * 1200)

        candles.append(Candle(t=t, o=float(o), h=float(h), l=float(l), c=float(c), v=v))
        price = c

    return [c.to_dict() for c in candles]
