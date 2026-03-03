# src/atlas/api/routes/presesion.py
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Dict, Any

from atlas.bot.presesion.engine import PRESESION_CONFIG, set_presesion_cfg

router = APIRouter(prefix="/presesion", tags=["presesion"])


class PresesionSetBody(BaseModel):
    enabled: bool = Field(True)
    tf_ref: str = Field("M15")
    tf_confirm: str = Field("M5")
    note: str = Field("Contexto previo a NY, solo aviso/diagnóstico")


@router.post("/set")
def presesion_set(body: PresesionSetBody) -> Dict[str, Any]:
    set_presesion_cfg(body.model_dump())
    return {"ok": True, "cfg": PRESESION_CONFIG}
