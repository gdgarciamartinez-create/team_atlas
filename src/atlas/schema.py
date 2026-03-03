from pydantic import BaseModel
from typing import Optional, Literal

class AiDecisionOut(BaseModel):
    decision: Literal["APPROVE", "WAIT", "REJECT"]
    reason_short: str
    reason_long: str
    confidence: int
    
    # Levels
    entry: float
    sl: float
    tp1: float
    tp2: Optional[float] = None
    partial: str
    lot_1pct: float
    cooldown_min: int