from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from atlas.service import ai_service
from atlas.schema import AiDecisionOut

router = APIRouter(prefix="/ai", tags=["AI"])

class EvaluateRequest(BaseModel):
    setup_id: str
    symbol: str
    mode: str
    direction: str
    zone_low: float
    zone_high: float
    tfs: List[str]
    notes: Optional[str] = ""
    snapshot: Dict[str, Any]

@router.post("/evaluate", response_model=AiDecisionOut)
def evaluate_setup(req: EvaluateRequest):
    setup_data = req.dict(exclude={"snapshot"})
    return ai_service.evaluate(setup_data, req.snapshot)