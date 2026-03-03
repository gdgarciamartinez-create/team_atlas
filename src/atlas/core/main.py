# src/atlas/api/main.py
from fastapi import FastAPI
from atlas.api.routes import motor_doctrinal, simulation, feed
from atlas.api import audit, alerts, execution

app = FastAPI(
    title="TEAM ATLAS API",
    description="Motor de análisis y diagnóstico para TEAM ATLAS.",
    version="1.0.0",
)

# Routers principales de la nueva arquitectura
app.include_router(motor_doctrinal.router, prefix="/api")
app.include_router(simulation.router, prefix="/api")
app.include_router(feed.router, prefix="/api", tags=["Feed"])

# Routers existentes
app.include_router(audit.router, prefix="/api", tags=["Auditoría"])
app.include_router(alerts.router, prefix="/api", tags=["Alertas"])
app.include_router(execution.router, prefix="/api", tags=["Execution (Legacy)"])

@app.get("/")
def read_root():
    return {"project": "TEAM ATLAS", "status": "running"}