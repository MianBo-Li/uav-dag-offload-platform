from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import AppError


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "request_id": request.headers.get("X-Request-Id"),
            }
        },
    )


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="UAV DAG Offload Platform",
        version="0.1.0",
        debug=settings.app_debug,
    )
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    app.add_exception_handler(AppError, app_error_handler)
    return app


app = create_app()
