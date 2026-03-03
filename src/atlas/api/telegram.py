from __future__ import annotations
import os
import requests

def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()

def send_telegram(text: str) -> tuple[bool, str]:
    token = _env("TELEGRAM_BOT_TOKEN")
    chat_id = _env("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        return False, "Faltan env vars: TELEGRAM_BOT_TOKEN y/o TELEGRAM_CHAT_ID"

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(url, json=payload, timeout=8)
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}: {r.text[:200]}"
        return True, "OK"
    except Exception as e:
        return False, f"EXC: {e}"