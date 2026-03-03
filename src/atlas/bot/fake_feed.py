import time
import random

class FakeFeed:
    def __init__(self):
        self.running = False
        self.candles = []
        self.price = 2000.0
        self.last_ts = int(time.time())

    def play(self):
        self.running = True

    def pause(self):
        self.running = False

    def step(self):
        if not self.running:
            return

        now = int(time.time())
        if now == self.last_ts:
            return

        self.last_ts = now

        o = self.price
        c = o + random.uniform(-1.5, 1.5)
        h = max(o, c) + random.uniform(0, 0.5)
        l = min(o, c) - random.uniform(0, 0.5)

        self.price = c
        self.candles.append({
            "time": now * 1000,   # IMPORTANTE: milisegundos
            "open": round(o, 2),
            "high": round(h, 2),
            "low": round(l, 2),
            "close": round(c, 2),
        })

        self.candles = self.candles[-200:]
