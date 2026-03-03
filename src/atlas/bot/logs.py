from collections import deque
from datetime import datetime, timezone

LOGS = deque(maxlen=300)

def push_log(level: str, msg: str):
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": str(level).upper(),
        "msg": str(msg),
    }
    LOGS.appendleft(entry)
    print(f"[{entry['level']}] {entry['msg']}")