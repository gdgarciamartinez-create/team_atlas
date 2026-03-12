import os
import json
import time
from typing import Optional
import urllib.request
import urllib.parse

# Env vars:
# ATLAS_TELEGRAM_BOT_TOKEN="8422955778"
# ATLAS_TELEGRAM_CHAT_ID="5372780169"

_STATE_PATH = os.path.join(os.path.dirname(__file__), "runtime", "telegram_state.json")

def _load_state():
    try:
        with open(_STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"sent_hashes": {}, "last_ts": 0}

def _save_state(st):
    os.makedirs(os.path.dirname(_STATE_PATH), exist_ok=True)
    with open(_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=2)

def send_signal_once(plan_hash: str, text: str) -> str:
    """
    Envia alerta SOLO una vez por plan_hash.
    Retorna: "SENT" | "SKIP_DUP" | "NO_CFG" | "ERR:<msg>"
    """
    token = os.getenv("ATLAS_TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("ATLAS_TELEGRAM_CHAT_ID", "").strip()

    if not token or not chat_id:
        return "NO_CFG"

    if not plan_hash:
        # sin hash no podemos deduplicar, preferimos no spamear
        return "NO_HASH"

    st = _load_state()
    sent = st.get("sent_hashes", {})

    if plan_hash in sent:
        return "SKIP_DUP"

    # anti-flood mínimo
    now = int(time.time())
    last_ts = int(st.get("last_ts", 0))
    if now - last_ts < 2:
        return "SKIP_RATE"

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True
        }).encode("utf-8")

        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=6) as resp:
            _ = resp.read().decode("utf-8", errors="ignore")

        sent[plan_hash] = now
        st["sent_hashes"] = sent
        st["last_ts"] = now
        _save_state(st)
        return "SENT"
    except Exception as e:
        return f"ERR:{e}"