from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from atlas.api.routes.router import router as api_router


app = FastAPI(
    title="TEAM ATLAS API",
    version="0.1.0",
)

# Router único, TODO bajo /api
app.include_router(api_router, prefix="/api")


@app.get("/")
def root():
    return {"ok": True, "service": "atlas", "note": "root"}


# Compat: si alguien espera /api/docs
@app.get("/api/docs", include_in_schema=False)
def api_docs_redirect():
    return RedirectResponse(url="/docs")


# Compat: si alguien espera /api/openapi.json
@app.get("/api/openapi.json", include_in_schema=False)
def api_openapi_redirect():
    return RedirectResponse(url="/openapi.json")