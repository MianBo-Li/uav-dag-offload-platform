from json import loads
from urllib.error import URLError

from app.core.config import Settings
from app.services.dead_letter_queue_service import RabbitMQDeadLetterQueueService


class FakeRabbitMQResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeRabbitMQResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


def _settings(**overrides: object) -> Settings:
    values = {
        "rabbitmq_queue_monitoring_enabled": True,
        "rabbitmq_management_url": "http://rabbitmq:15672/api",
        "rabbitmq_management_username": "guest",
        "rabbitmq_management_password": "guest",
        "rabbitmq_management_vhost": "/",
        "rabbitmq_management_timeout_seconds": 1.0,
        "celery_task_dead_letter_queue": "uav_dag_execution.dlq",
    }
    values.update(overrides)
    return Settings(**values)


def test_dead_letter_queue_peek_returns_disabled_result_when_monitoring_disabled() -> None:
    result = RabbitMQDeadLetterQueueService(
        _settings(rabbitmq_queue_monitoring_enabled=False)
    ).peek_messages(limit=10, truncate=4096)

    assert result.queue_name == "uav_dag_execution.dlq"
    assert result.enabled is False
    assert result.available is False
    assert result.items == []


def test_dead_letter_queue_peek_uses_requeue_ackmode(monkeypatch) -> None:
    captured_urls: list[str] = []
    captured_bodies: list[dict[str, object]] = []

    def fake_urlopen(request, timeout: float):
        captured_urls.append(request.full_url)
        captured_bodies.append(loads(request.data.decode("utf-8")))
        assert timeout == 1.0
        return FakeRabbitMQResponse(
            b"""
            [
              {
                "payload": {"execution_id": "00000000-0000-0000-0000-000000000001"},
                "payload_encoding": "string",
                "exchange": "uav_dag_execution",
                "routing_key": "uav_dag_execution",
                "redelivered": true,
                "message_count": 2,
                "properties": {
                  "headers": {
                    "x-death": []
                  },
                  "delivery_mode": 2
                }
              }
            ]
            """
        )

    monkeypatch.setattr(
        "app.services.dead_letter_queue_service.urlopen",
        fake_urlopen,
    )

    result = RabbitMQDeadLetterQueueService(_settings()).peek_messages(
        limit=5,
        truncate=1024,
    )

    assert captured_urls == [
        "http://rabbitmq:15672/api/queues/%2F/uav_dag_execution.dlq/get"
    ]
    assert captured_bodies == [
        {
            "count": 5,
            "ackmode": "ack_requeue_true",
            "encoding": "auto",
            "truncate": 1024,
        }
    ]
    assert result.enabled is True
    assert result.available is True
    assert len(result.items) == 1
    assert result.items[0].payload == {
        "execution_id": "00000000-0000-0000-0000-000000000001"
    }
    assert result.items[0].redelivered is True
    assert result.items[0].message_count == 2
    assert result.items[0].headers == {"x-death": []}


def test_dead_letter_queue_peek_handles_unreachable_rabbitmq(monkeypatch) -> None:
    def fake_urlopen(request, timeout: float):
        raise URLError("rabbitmq unavailable")

    monkeypatch.setattr(
        "app.services.dead_letter_queue_service.urlopen",
        fake_urlopen,
    )

    result = RabbitMQDeadLetterQueueService(_settings()).peek_messages(
        limit=5,
        truncate=1024,
    )

    assert result.enabled is True
    assert result.available is False
    assert result.items == []
    assert result.error_message is not None
