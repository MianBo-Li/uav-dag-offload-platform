from fastapi import APIRouter, Query

from app.core.config import get_settings
from app.schemas.dead_letter_queue import (
    DeadLetterQueueMessageRead,
    DeadLetterQueueMessageListResponse,
    DeadLetterQueueSnapshotResponse,
)
from app.services.dead_letter_queue_service import RabbitMQDeadLetterQueueService
from app.services.queue_monitoring_service import RabbitMQQueueMonitoringService

router = APIRouter(prefix="/dead-letter-queue")


@router.get("", response_model=DeadLetterQueueSnapshotResponse)
def get_dead_letter_queue_snapshot() -> DeadLetterQueueSnapshotResponse:
    settings = get_settings()
    queue_snapshot = next(
        snapshot
        for snapshot in RabbitMQQueueMonitoringService(settings).load_snapshots()
        if snapshot.queue_name == settings.celery_task_dead_letter_queue
    )
    return DeadLetterQueueSnapshotResponse(
        queue_name=queue_snapshot.queue_name,
        enabled=queue_snapshot.enabled,
        available=queue_snapshot.available,
        messages=queue_snapshot.messages,
        messages_ready=queue_snapshot.messages_ready,
        messages_unacknowledged=queue_snapshot.messages_unacknowledged,
        consumers=queue_snapshot.consumers,
    )


@router.get("/messages", response_model=DeadLetterQueueMessageListResponse)
def peek_dead_letter_queue_messages(
    limit: int = Query(default=10, ge=1, le=100),
    truncate: int = Query(default=4096, ge=1, le=100_000),
) -> DeadLetterQueueMessageListResponse:
    result = RabbitMQDeadLetterQueueService().peek_messages(
        limit=limit,
        truncate=truncate,
    )
    return DeadLetterQueueMessageListResponse(
        queue_name=result.queue_name,
        enabled=result.enabled,
        available=result.available,
        items=[
            DeadLetterQueueMessageRead(
                payload=item.payload,
                payload_encoding=item.payload_encoding,
                exchange=item.exchange,
                routing_key=item.routing_key,
                redelivered=item.redelivered,
                message_count=item.message_count,
                properties=item.properties,
                headers=item.headers,
            )
            for item in result.items
        ],
        error_message=result.error_message,
    )
