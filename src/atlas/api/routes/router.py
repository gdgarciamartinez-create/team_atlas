from fastapi import APIRouter

from atlas.api.routes.status import router as status_router
from atlas.api.routes.control import router as control_router
from atlas.api.routes.snapshot import router as snapshot_router
from atlas.api.routes.scan import router as scan_router
from atlas.api.routes.bitacora import router as bitacora_router
from atlas.api.routes.stats import router as stats_router
from atlas.api.routes.audit_stats import router as audit_stats_router

router = APIRouter()

router.include_router(status_router)
router.include_router(control_router)
router.include_router(snapshot_router)
router.include_router(scan_router)
router.include_router(bitacora_router)
router.include_router(stats_router)
router.include_router(audit_stats_router)


@router.get("/ping-routes")
def ping_routes():
    return {"ok": True, "msg": "router central vivo"}