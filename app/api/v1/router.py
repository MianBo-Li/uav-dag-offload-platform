from fastapi import APIRouter

from app.api.v1.endpoints import health, nodes

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(nodes.router, tags=["nodes"])
