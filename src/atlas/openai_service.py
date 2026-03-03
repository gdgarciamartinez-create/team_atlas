from __future__ import annotations
import logging
import requests
from typing import Dict, Any
from atlas.models import AIResult

logger = logging.getLogger("atlas.openai")

class OpenAIService:
    def __init__(self, api_key: str, base_url: str, model: str, timeout_s: int = 20) -> None:
        self.api_key = (api_key or "").strip()
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.model = model
        self.timeout_s = timeout_s

    @property
    def enabled(self) -> bool:
        return bool(self.api_key) and bool(self.model)

    def judge(self, payload: Dict[str, Any]) -> AIResult:
        if not self.enabled:
            return AIResult(ok=False, reason="IA no configurada")

        system = (
            "Eres el juez final del TEAM ATLAS. Responde SOLO JSON: "
            '{"ok": true/false, "reason": "texto corto"} '
            "Si gatillo débil, RR malo, o falta claridad => ok=false."
        )

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": str(payload)},
            ],
            "temperature": 0.1,
        }

        try:
            r = requests.post(url, headers=headers, json=body, timeout=self.timeout_s)
            if r.status_code >= 400:
                logger.error("OpenAI error %s: %s", r.status_code, r.text[:300])
                return AIResult(ok=False, reason="IA fallo http")

            data = r.json()
            text = data["choices"][0]["message"]["content"].strip()

            import json
            try:
                obj = json.loads(text)
                return AIResult(ok=bool(obj.get("ok", False)), reason=str(obj.get("reason", ""))[:160])
            except Exception:
                return AIResult(ok=False, reason="IA formato inválido")
        except Exception as e:
            logger.exception("OpenAI exception: %s", e)
            return AIResult(ok=False, reason="IA no respondió")
