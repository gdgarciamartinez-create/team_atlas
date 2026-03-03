# LEGACY NEUTRALIZADO.
# Este archivo NO se usa en la arquitectura actual.
# Si luego querés ejecución real, se crea en:
#   src/atlas/api/routes/execution.py
# y se incluye SOLO desde src/atlas/api/routes/__init__.py

from fastapi import APIRouter

router = APIRouter()

@router.get("/execution_disabled")
def execution_disabled():
    return {"ok": False, "reason": "legacy execution disabled"}
