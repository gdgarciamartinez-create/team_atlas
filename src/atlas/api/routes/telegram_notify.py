from __future__ import annotations
from typing import Tuple
import os
import time
import hashlib

try:
    import requests
except Exception:
    requests = None

# Anti-spam simple en memoria
_LAST_SENT: dict[str, int] = {}

def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()

def telegram_enabled() -> bool:
    return bool(_env("TELEGRAM_BOT_TOKEN") and _env("TELEGRAM_CHAT_ID") and requests is not None)

def _fingerprint(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()

def can_send(text: str, cooldown_sec: int = 600) -> Tuple[bool, str]:
    fp = _fingerprint(text)
    now = int(time.time())
    last = _LAST_SENT.get(fp, 0)
    if (now - last) < cooldown_sec:
        return False, "COOLDOWN"
    _LAST_SENT[fp] = now
    return True, "OK"

def send_telegram(text: str) -> Tuple[bool, str]:
    if not telegram_enabled():
        return False, "TELEGRAM_DISABLED_OR_MISSING_ENV"

    token = _env("TELEGRAM_BOT_TOKEN")
    chat_id = _env("TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    payload = {"chat_id": chat_id, "text": text}
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code != 200:
            return False, f"TELEGRAM_HTTP_{r.status_code}"
        return True, "OK"
    except Exception as e:
        return False, f"TELEGRAM_EXCEPTION:{type(e).__name__}"