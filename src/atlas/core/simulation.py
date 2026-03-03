# src/atlas/api/routes/simulation.py
from __future__ import annotations
from fastapi import APIRouter

from atlas.bot.state import BOT_STATE

router = APIRouter()


@router.post("/sim/reset", tags=["Simulación"])
def reset_simulation_state():
    """
    Resetea estados de simulación, como el cierre de escenario.
    """
    BOT_STATE["scenario"] = {"closed": False, "reason": "", "closed_ts": 0}
    return {"ok": True, "message": "Simulation state reset."}