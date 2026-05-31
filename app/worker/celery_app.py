from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "uav_dag_offload_platform",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    accept_content=["json"],
    enable_utc=True,
    result_serializer="json",
    task_default_queue=settings.celery_task_default_queue,
    task_serializer="json",
    task_track_started=True,
    timezone="UTC",
)
