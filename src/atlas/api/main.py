from __future__ import annotations

from fastapi import FastAPI
from atlas.api.routes.router import router as api_router

app = FastAPI(title="TEAM ATLAS API", version="1.0.0")

# Prefijo /api se define SOLO ACÁ (para evitar /api/api)
app.include_router(api_router, prefix="/api")

@app.get("/")
def root():
    return {"ok": True, "service": "TEAM_ATLAS", "hint": "Try /api/status or /docs"}