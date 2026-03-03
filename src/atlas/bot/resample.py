# src/atlas/bot/resample.py
from __future__ import annotations

from typing import List, Dict

TF_TO_MIN = {
    "M1": 1,
    "M3": 3,
    "M5": 5,
    "M15": 15,
    "M30": 30,
    "H1": 60,
    "H4": 240,
    "H8": 480,
    "D1": 1440,
}

def resample_ohlc(candles: List[dict], tf: str) -> List[Dict]:
    """
    candles: lista M1-like con time en segundos.
    Resample simple agrupando por bloques de N minutos.
    """
    if tf not in TF_TO_MIN or tf == "M1":
        return candles[:] if isinstance(candles, list) else []

    if not candles or not isinstance(candles, list):
        return []

    block_min = TF_TO_MIN[tf]
    block_sec = block_min * 60

    out = []
    bucket = []
    bucket_start = None

    for c in candles:
        t = int(c.get("time", 0))
        if t <= 0:
            continue
        start = (t // block_sec) * block_sec
        if bucket_start is None:
            bucket_start = start

        if start != bucket_start and bucket:
            out.append(_agg_bucket(bucket, bucket_start))
            bucket = []
            bucket_start = start

        bucket.append(c)

    if bucket:
        out.append(_agg_bucket(bucket, bucket_start))

    return out

def _agg_bucket(bucket: List[dict], bucket_start: int) -> Dict:
    o = float(bucket[0]["open"])
    h = max(float(x["high"]) for x in bucket)
    l = min(float(x["low"]) for x in bucket)
    c = float(bucket[-1]["close"])
    return {"time": bucket_start, "open": o, "high": h, "low": l, "close": c}