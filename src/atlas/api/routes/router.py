from __future__ import annotations

from fastapi import APIRouter

# Router agregador ÚNICO (SIN prefix="/api")
router = APIRouter()

# Rutas base (V1)
from atlas.api.routes.status import router as status_router
from atlas.api.routes.snapshot import router as snapshot_router

router.include_router(status_router)
router.include_router(snapshot_router)

# Rutas opcionales existentes (si están, se agregan; si no, no rompen)
def _try_include(import_path: str, attr: str = "router"):
    try:
        mod = __import__(import_path, fromlist=[attr])
        r = getattr(mod, attr)
        router.include_router(r)
    except Exception:
        pass

_try_include("atlas.api.routes.bitacora")
_try_include("atlas.api.routes.armed_state")
_try_include("atlas.api.routes.exec")
_try_include("atlas.api.routes.mt5")
_try_include("atlas.api.routes.state")
_try_include("atlas.api.routes.telemetry")
_try_include("atlas.api.routes.simulation")
_try_include("atlas.api.routes.robusta")
_try_include("atlas.api.routes.module_reports")
_try_include("atlas.api.routes.world_config")
_try_include("atlas.api.routes.atlas_ai")
_try_include("atlas.api.routes.motor_min")
_try_include("atlas.api.routes.motor_doctrinal")
_try_include("atlas.api.routes.config")
_try_include("atlas.api.routes.enums")