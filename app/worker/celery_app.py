from celery import Celery
from celery.signals import worker_ready
from celery.utils.log import get_task_logger
from kombu import Exchange, Queue

from app.core.config import Settings
from app.core.config import get_settings

logger = get_task_logger(__name__)
settings = get_settings()


def build_dead_letter_exchange(settings: Settings) -> Exchange:
    return Exchange(
        settings.celery_task_dead_letter_exchange,
        type="direct",
        durable=True,
    )


def build_dead_letter_queue(settings: Settings) -> Queue:
    return Queue(
        settings.celery_task_dead_letter_queue,
        exchange=build_dead_letter_exchange(settings),
        routing_key=settings.celery_task_dead_letter_routing_key,
        durable=True,
    )


def build_execution_queue(settings: Settings) -> Queue:
    return Queue(
        settings.celery_task_default_queue,
        exchange=Exchange(
            settings.celery_task_default_exchange,
            type="direct",
            durable=True,
        ),
        routing_key=settings.celery_task_default_routing_key,
        durable=True,
        queue_arguments={
            "x-dead-letter-exchange": settings.celery_task_dead_letter_exchange,
            "x-dead-letter-routing-key": settings.celery_task_dead_letter_routing_key,
        },
    )


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
    task_acks_late=True,
    task_default_queue=settings.celery_task_default_queue,
    task_default_exchange=settings.celery_task_default_exchange,
    task_default_exchange_type="direct",
    task_default_routing_key=settings.celery_task_default_routing_key,
    task_queues=(build_execution_queue(settings),),
    task_reject_on_worker_lost=True,
    task_serializer="json",
    task_track_started=True,
    timezone="UTC",
    worker_prefetch_multiplier=1,
)


def declare_dead_letter_topology(settings: Settings) -> None:
    dead_letter_exchange = build_dead_letter_exchange(settings)
    dead_letter_queue = build_dead_letter_queue(settings)
    with celery_app.connection_for_write() as connection:
        with connection.channel() as channel:
            dead_letter_exchange.bind(channel).declare()
            dead_letter_queue.bind(channel).declare()


@worker_ready.connect
def declare_worker_dead_letter_topology(**_: object) -> None:
    try:
        declare_dead_letter_topology(settings)
    except Exception:
        logger.warning("Failed to declare RabbitMQ dead-letter topology", exc_info=True)
