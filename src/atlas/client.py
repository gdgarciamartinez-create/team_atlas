import logging
import requests
import json
from typing import Dict, Any, Optional
from atlas.config import settings

logger = logging.getLogger("atlas.ai.client")

class OpenAIClient:
    def __init__(self):
        self.api_key = settings.openai_api_key
        self.base_url = settings.openai_base_url.rstrip("/")
        self.model = settings.openai_model
        self.timeout = settings.openai_timeout_s

    def chat_completion(self, system: str, user_content: str) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            logger.error("OpenAI API Key missing")
            return None

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }

        try:
            r = requests.post(url, headers=headers, json=body, timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"OpenAI Request Error: {e}")
            return None