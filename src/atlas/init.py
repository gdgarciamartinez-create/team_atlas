from fastapi import APIRouter
from atlas.api.routes.status import router as status_router
from atlas.api.routes.snapshot import router as snapshot_router
from atlas.api.routes.control import router as control_router
from atlas.api.routes.mt5 import router as mt5_router

api_router = APIRouter()
api_router.include_router(status_router)
api_router.include_router(snapshot_router)
api_router.include_router(control_router)
api_router.include_router(mt5_router)