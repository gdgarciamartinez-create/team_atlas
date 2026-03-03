from __future__ import annotations
import logging
import requests

from atlas.config import settings

logger = logging.getLogger("atlas.telegram")

class TelegramNotifier:
    def __init__(self, token: str, chat_id: str, timeout_s: int = 10) -> None:
        self.token = (token or "").strip()
        self.chat_id = str(chat_id or "").strip()
        self.timeout_s = timeout_s

    @property
    def enabled(self) -> bool:
        return bool(self.token) and bool(self.chat_id)

    def send(self, text: str) -> bool:
        if not self.enabled:
            logger.error("Telegram deshabilitado: falta token/chat_id")
            return False
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": text}
        try:
            r = requests.post(url, json=payload, timeout=self.timeout_s)
            if r.status_code >= 400:
                logger.error("Telegram error %s: %s", r.status_code, r.text[:300])
                return False
            return True
        except Exception as e:
            logger.exception("Telegram exception: %s", e)
            return False

_notifier = TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id)

def telegram_enabled() -> bool:
    return _notifier.enabled
