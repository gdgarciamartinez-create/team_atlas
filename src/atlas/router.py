from fastapi import APIRouter
from atlas.core.mt5_engine import get_candles, mt5_status

# Router agregador ÚNICO
router = APIRouter()

# Importar routers reales
from atlas.api.routes.status import router as status_router
from atlas.api.routes.snapshot import router as snapshot_router

# Incluir subrouters
router.include_router(status_router)
router.include_router(snapshot_router)
