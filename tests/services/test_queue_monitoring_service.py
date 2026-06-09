from urllib.error import URLError

from app.core.config import Settings
from app.services.queue_monitoring_service import RabbitMQQueueMonitoringService


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
        "celery_task_default_queue": "uav_dag_execution",
    }
    values.update(overrides)
    return Settings(**values)


def test_queue_monitoring_returns_disabled_snapshot() -> None:
    snapshot = RabbitMQQueueMonitoringService(
        _settings(rabbitmq_queue_monitoring_enabled=False)
    ).load_snapshot()

    assert snapshot.queue_name == "uav_dag_execution"
    assert snapshot.enabled is False
    assert snapshot.available is False
    assert snapshot.messages == 0
    assert snapshot.consumers == 0


def test_queue_monitoring_reads_rabbitmq_queue_payload(monkeypatch) -> None:
    captured_urls: list[str] = []

    def fake_urlopen(request, timeout: float):
        captured_urls.append(request.full_url)
        assert timeout == 1.0
        return FakeRabbitMQResponse(
            b"""
            {
              "messages": 7,
              "messages_ready": 5,
              "messages_unacknowledged": 2,
              "consumers": 1
            }
            """
        )

    monkeypatch.setattr(
        "app.services.queue_monitoring_service.urlopen",
        fake_urlopen,
    )

    snapshot = RabbitMQQueueMonitoringService(_settings()).load_snapshot()

    assert captured_urls == [
        "http://rabbitmq:15672/api/queues/%2F/uav_dag_execution"
    ]
    assert snapshot.enabled is True
    assert snapshot.available is True
    assert snapshot.messages == 7
    assert snapshot.messages_ready == 5
    assert snapshot.messages_unacknowledged == 2
    assert snapshot.consumers == 1


def test_queue_monitoring_handles_unreachable_rabbitmq(monkeypatch) -> None:
    def fake_urlopen(request, timeout: float):
        raise URLError("rabbitmq unavailable")

    monkeypatch.setattr(
        "app.services.queue_monitoring_service.urlopen",
        fake_urlopen,
    )

    snapshot = RabbitMQQueueMonitoringService(_settings()).load_snapshot()

    assert snapshot.enabled is True
    assert snapshot.available is False
    assert snapshot.messages == 0
    assert snapshot.messages_ready == 0
    assert snapshot.messages_unacknowledged == 0
    assert snapshot.consumers == 0
