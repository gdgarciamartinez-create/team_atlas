import threading
import time
import random
from datetime import datetime, timedelta

from atlas.bot.state import STATE as BOT_STATE

_thread = None


def _engine():
    eng = BOT_STATE.setdefault("engine", {})
    if not isinstance(eng, dict):
        eng = {}
        BOT_STATE["engine"] = eng

    eng.setdefault("running", True)   # 👈 lo dejamos corriendo por defecto
    eng.setdefault("tick", 0)
    eng.setdefault("speed", 1.0)

    return eng


def _worker():
    print("[LOOP] started")

    price = 2000.0
    ts = datetime.now()

    BOT_STATE["candles"] = []

    while True:
        eng = _engine()

        running = bool(eng.get("running", True))
        speed = float(eng.get("speed", 1.0))

        if not running:
            time.sleep(0.2)
            continue

        candles = BOT_STATE.setdefault("candles", [])

        vol = 0.8
        delta = (random.random() - 0.5) * 2 * vol

        close_p = price + delta
        high_p = max(price, close_p) + random.random() * 0.3
        low_p = min(price, close_p) - random.random() * 0.3

        ts += timedelta(minutes=1)

        candles.append({
            "time": int(ts.timestamp()),
            "open": round(price, 2),
            "high": round(high_p, 2),
            "low": round(low_p, 2),
            "close": round(close_p, 2),
        })

        price = close_p

        if len(candles) > 300:
            candles[:] = candles[-300:]

        eng["tick"] += 1
        BOT_STATE["tick"] = eng["tick"]

        time.sleep(max(0.1, 1.0 / max(0.1, speed)))


def start_loop():
    global _thread
    if _thread is None or not _thread.is_alive():
        _thread = threading.Thread(target=_worker, daemon=True)
        _thread.start()
        print("[LOOP] thread launched")