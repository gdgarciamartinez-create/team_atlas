from fastapi import FastAPI
from atlas.api.routes import api_router

def build_app():
    app = FastAPI(title="ATLAS API")
    app.include_router(api_router, prefix="/api")

    @app.on_event("startup")
    async def _startup():
        from atlas.bot.loop import start_loop
        start_loop()
        print("[ATLAS] bot loop started")

    return app

app = build_app()