from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from atlas.api.routes.stats import router as stats_router

# Import routers (blindado: si algo falta, el backend igual arranca)
try:
    from atlas.api.routes.status import router as status_router  # type: ignore
except Exception:
    status_router = None  # type: ignore

try:
    from atlas.api.routes.snapshot import router as snapshot_router  # type: ignore
except Exception:
    snapshot_router = None  # type: ignore

# (Opcional) lo agregaremos en el próximo paso cuando creemos plan.py
try:
    from atlas.api.routes.plan import router as plan_router  # type: ignore
except Exception:
    plan_router = None  # type: ignore


app = FastAPI(title="TEAM ATLAS API", version="1.0.0")

# CORS (por si accedes desde Vite/host distinto)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router agregador único (mandamiento)
if status_router is not None:
    app.include_router(status_router, prefix="/api")

if snapshot_router is not None:
    app.include_router(snapshot_router, prefix="/api")

if plan_router is not None:
    app.include_router(plan_router, prefix="/api")


@app.get("/api/health")
def health():
    return {"ok": True}