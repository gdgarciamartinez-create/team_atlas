import time
from datetime import datetime

def now_ts() -> float:
    return time.time()

def ts_to_iso(ts: float) -> str:
    return datetime.fromtimestamp(ts).isoformat()