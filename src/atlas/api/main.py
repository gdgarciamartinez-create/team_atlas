from fastapi import FastAPI

from atlas.api.routes import api_router


def build_app() -> FastAPI:
    app = FastAPI(title="ATLAS API")

    # Todas las rutas bajo /api
    app.include_router(api_router, prefix="/api")

    @app.on_event("startup")
    async def _startup():
        try:
            from atlas.bot.loop import start_loop
            start_loop()
            print("[ATLAS] bot loop started")
        except Exception as e:
            print(f"[ATLAS] startup warning: {e!r}")

    return app


app = build_app()