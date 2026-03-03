from __future__ import annotations

from fastapi import FastAPI
from atlas.api.routes.router import router as api_router

app = FastAPI(title="TEAM ATLAS API")

# TODO tuyo: si tenías CORS acá, lo volvemos a meter luego.
# Por ahora, lo importante: que /api/* exista.

app.include_router(api_router, prefix="/api")