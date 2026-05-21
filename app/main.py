from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="UAV DAG Offload Platform",
        version="0.1.0",
        debug=settings.app_debug,
    )
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
