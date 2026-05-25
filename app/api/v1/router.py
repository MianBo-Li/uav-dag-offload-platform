from fastapi import APIRouter

from app.api.v1.endpoints import health, nodes, tasks

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(nodes.router, tags=["nodes"])
api_router.include_router(tasks.router, tags=["tasks"])
