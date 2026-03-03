from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List
import time
import pandas as pd
import yfinance as yf

from .resilience import with_retry, RetryPolicy, is_stale

@dataclass
class Candle:
    ts: int
    o: float
    h: float
    l: float
    c: float
    v: float

class YahooDataSourceReal:
    def __init__(self, symbol_map: Dict[str, str], interval: str, period: str, max_stale_s: int = 60*20):
        self.symbol_map = symbol_map
        self.interval = interval
        self.period = period
        self.max_stale_s = max_stale_s
        self._cache: Dict[str, List[Candle]] = {}
        self._cache_ts: Dict[str, int] = {}
        self.policy = RetryPolicy(tries=4, base_delay_s=0.6, max_delay_s=5.0)

    def _download(self, ticker: str):
        return yf.download(
            tickers=ticker,
            period=self.period,
            interval=self.interval,
            auto_adjust=False,
            progress=False,
            threads=False,
        )

    def fetch(self, symbol: str, max_candles: int = 500) -> List[Candle]:
        ticker = self.symbol_map.get(symbol)
        if not ticker:
            return []

        now = int(time.time())
        # cache liviano 15s
        if symbol in self._cache and (now - self._cache_ts.get(symbol, 0) < 15):
            return self._cache[symbol]

        def go():
            df = self._download(ticker)
            if df is None or df.empty:
                return []
            df = df.rename(columns={"Open":"open","High":"high","Low":"low","Close":"close","Volume":"volume"})
            df = df.tail(max_candles)
            candles: List[Candle] = []
            for idx, row in df.iterrows():
                ts = int(pd.Timestamp(idx).timestamp())
                candles.append(Candle(
                    ts=ts,
                    o=float(row["open"]),
                    h=float(row["high"]),
                    l=float(row["low"]),
                    c=float(row["close"]),
                    v=float(row.get("volume", 0.0) if pd.notna(row.get("volume", 0.0)) else 0.0),
                ))
            # stale guard: última vela demasiado vieja => invalid
            if candles and is_stale(candles[-1].ts, self.max_stale_s):
                return []
            return candles

        candles = with_retry(go, self.policy)
        self._cache[symbol] = candles
        self._cache_ts[symbol] = now
        return candles