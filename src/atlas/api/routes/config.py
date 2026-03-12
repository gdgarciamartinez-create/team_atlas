from fastapi import APIRouter

# Importamos el router de FEED y lo incluimos aquí
from .feed import router as feed_router

router = APIRouter(prefix="/config", tags=["config"])

# ✅ Engancha feed bajo /api/feed/*
# (OJO: el prefix /api lo pone el loader de la app, acá solo definimos /feed)
router.include_router(feed_router)


@router.get("/ping")
def ping():
    # Endpoint inocuo para probar rápidamente que config está cargado
    return {"ok": True, "route": "/config/ping"}