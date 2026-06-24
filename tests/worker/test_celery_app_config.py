from app.core.config import Settings
from app.worker.celery_app import (
    build_dead_letter_exchange,
    build_dead_letter_queue,
    build_execution_queue,
    celery_app,
)


def test_execution_queue_declares_dead_letter_arguments() -> None:
    settings = Settings(
        celery_task_default_queue="execution",
        celery_task_default_exchange="execution.exchange",
        celery_task_default_routing_key="execution.run",
        celery_task_dead_letter_exchange="execution.dlx",
        celery_task_dead_letter_routing_key="execution.dead",
    )

    queue = build_execution_queue(settings)

    assert queue.name == "execution"
    assert queue.exchange.name == "execution.exchange"
    assert queue.routing_key == "execution.run"
    assert queue.queue_arguments == {
        "x-dead-letter-exchange": "execution.dlx",
        "x-dead-letter-routing-key": "execution.dead",
    }


def test_dead_letter_queue_uses_dead_letter_exchange_and_routing_key() -> None:
    settings = Settings(
        celery_task_dead_letter_exchange="execution.dlx",
        celery_task_dead_letter_routing_key="execution.dead",
        celery_task_dead_letter_queue="execution.dlq",
    )

    exchange = build_dead_letter_exchange(settings)
    queue = build_dead_letter_queue(settings)

    assert exchange.name == "execution.dlx"
    assert exchange.type == "direct"
    assert queue.name == "execution.dlq"
    assert queue.exchange.name == "execution.dlx"
    assert queue.routing_key == "execution.dead"


def test_worker_only_consumes_execution_queue_by_default() -> None:
    configured_queue_names = {queue.name for queue in celery_app.conf.task_queues}

    assert "uav_dag_execution" in configured_queue_names
    assert "uav_dag_execution.dlq" not in configured_queue_names
