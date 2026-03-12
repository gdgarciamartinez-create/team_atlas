from fastapi import FastAPI

from atlas.api.routes.status import router as status_router
from atlas.api.routes.control import router as control_router
from atlas.api.routes.snapshot import router as snapshot_router
from atlas.api.routes.bitacora import router as bitacora_router

app = FastAPI(title="TEAM ATLAS API")

app.include_router(status_router, prefix="/api")
app.include_router(control_router, prefix="/api")
app.include_router(snapshot_router)
app.include_router(bitacora_router, prefix="/api")