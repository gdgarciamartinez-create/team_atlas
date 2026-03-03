from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Query

from atlas.bot.bitacora.store import read_rows, compute_stats, wipe

router = APIRouter(prefix="/bitacora", tags=["bitacora"])


@router.get("/recent")
def bitacora_recent(
    limit: int = Query(50, ge=1, le=2000),
) -> Dict[str, Any]:
    rows = read_rows(limit=limit)
    return {"ok": True, "limit": int(limit), "rows": rows}


@router.get("/stats")
def bitacora_stats(
    limit: int = Query(500, ge=1, le=2000),
) -> Dict[str, Any]:
    stats = compute_stats(limit=limit)
    return {"ok": True, "stats": stats}


@router.post("/wipe")
def bitacora_wipe() -> Dict[str, Any]:
    # Laboratorio: borra el jsonl completo
    out = wipe()
    return {"ok": True, "wipe": out}