from __future__ import annotations
from typing import List, Dict, Any
import time
import random

def fake_candles(count: int, base: float) -> List[Dict[str, Any]]:
    now = int(time.time())
    n = max(50, min(int(count), 500))
    price = float(base)
    step = 60
    out: List[Dict[str, Any]] = []
    for i in range(n):
        ts = now - (n - i) * step
        o = price
        if base > 100:
            c = o + random.uniform(-5, 5)
            h = max(o, c) + random.uniform(0, 2)
            l = min(o, c) - random.uniform(0, 2)
        else:
            c = o + random.uniform(-0.003, 0.003)
            h = max(o, c) + random.uniform(0.0005, 0.002)
            l = min(o, c) - random.uniform(0.0005, 0.002)
        price = c
        out.append({"time": ts, "open": round(o, 5), "high": round(h, 5), "low": round(l, 5), "close": round(c, 5)})
    return out