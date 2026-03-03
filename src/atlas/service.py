import json
import logging
from typing import Any, Dict
from atlas.client import OpenAIClient
from atlas.schema import AiDecisionOut
from atlas.prompts import RULESET_V1
from atlas.config import settings

logger = logging.getLogger("atlas.ai.service")

class AiService:
    def __init__(self):
        self.client = OpenAIClient()

    def evaluate(self, setup_data: Dict[str, Any], snapshot: Dict[str, Any]) -> AiDecisionOut:
        if not settings.ai_enabled:
            return self._fallback_response("AI Disabled")

        # Construir payload para el prompt
        context = {
            "setup": setup_data,
            "snapshot": snapshot,
            "account": {
                "size": settings.account_size,
                "risk_pct": settings.risk_pct
            }
        }
        
        user_content = json.dumps(context, indent=2)
        
        response = self.client.chat_completion(RULESET_V1, user_content)
        
        if not response:
            return self._fallback_response("AI Unavailable")

        try:
            content = response["choices"][0]["message"]["content"]
            data = json.loads(content)
            return AiDecisionOut(**data)
        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")
            return self._fallback_response("Parse Error")

    def _fallback_response(self, reason: str) -> AiDecisionOut:
        return AiDecisionOut(
            decision="WAIT",
            reason_short=reason,
            reason_long=f"System fallback due to: {reason}",
            confidence=0,
            entry=0.0,
            sl=0.0,
            tp1=0.0,
            tp2=None,
            partial="N/A",
            lot_1pct=0.0,
            cooldown_min=10
        )

ai_service = AiService()