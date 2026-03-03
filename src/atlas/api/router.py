# src/atlas/api/routes/router.py

from fastapi import APIRouter

# importar subrouters reales
from atlas.api.routes.snapshot import router as snapshot_router
from atlas.api.routes.status import router as status_router
from atlas.api.routes.gatillo import router as gatillo_router

router = APIRouter()

# incluir subrutas
router.include_router(status_router)
router.include_router(snapshot_router)
router.include_router(gatillo_router)
