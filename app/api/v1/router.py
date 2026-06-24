from fastapi import APIRouter

from app.api.v1.endpoints import (
    dead_letter_queue,
    executions,
    health,
    nodes,
    schedules,
    tasks,
    worker_alerts,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(nodes.router, tags=["nodes"])
api_router.include_router(tasks.router, tags=["tasks"])
api_router.include_router(schedules.router, tags=["schedules"])
api_router.include_router(executions.router, tags=["executions"])
api_router.include_router(worker_alerts.router, tags=["worker-alerts"])
api_router.include_router(dead_letter_queue.router, tags=["dead-letter-queue"])
