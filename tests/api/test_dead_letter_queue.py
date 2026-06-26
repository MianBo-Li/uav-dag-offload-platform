from json import loads

from fastapi.testclient import TestClient

from app.core.config import Settings


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
        "celery_task_dead_letter_queue": "uav_dag_execution.dlq",
    }
    values.update(overrides)
    return Settings(**values)


def test_get_dead_letter_queue_snapshot(
    client: TestClient,
    monkeypatch,
) -> None:
    settings = _settings()

    def fake_get_settings() -> Settings:
        return settings

    def fake_urlopen(request, timeout: float):
        if request.full_url.endswith("/uav_dag_execution.dlq"):
            return FakeRabbitMQResponse(
                b"""
                {
                  "messages": 3,
                  "messages_ready": 3,
                  "messages_unacknowledged": 0,
                  "consumers": 0
                }
                """
            )
        return FakeRabbitMQResponse(
            b"""
            {
              "messages": 1,
              "messages_ready": 1,
              "messages_unacknowledged": 0,
              "consumers": 1
            }
            """
        )

    monkeypatch.setattr(
        "app.api.v1.endpoints.dead_letter_queue.get_settings",
        fake_get_settings,
    )
    monkeypatch.setattr(
        "app.services.queue_monitoring_service.urlopen",
        fake_urlopen,
    )

    response = client.get("/api/v1/dead-letter-queue")

    assert response.status_code == 200
    assert response.json() == {
        "queue_name": "uav_dag_execution.dlq",
        "enabled": True,
        "available": True,
        "messages": 3,
        "messages_ready": 3,
        "messages_unacknowledged": 0,
        "consumers": 0,
    }


def test_peek_dead_letter_queue_messages(
    client: TestClient,
    monkeypatch,
) -> None:
    settings = _settings()
    captured_bodies: list[dict[str, object]] = []

    def fake_get_settings() -> Settings:
        return settings

    def fake_urlopen(request, timeout: float):
        captured_bodies.append(loads(request.data.decode("utf-8")))
        return FakeRabbitMQResponse(
            b"""
            [
              {
                "payload": "execution-id-1",
                "payload_encoding": "string",
                "exchange": "uav_dag_execution",
                "routing_key": "uav_dag_execution",
                "redelivered": false,
                "message_count": 0,
                "properties": {
                  "headers": {
                    "x-first-death-queue": "uav_dag_execution"
                  }
                }
              }
            ]
            """
        )

    monkeypatch.setattr(
        "app.services.dead_letter_queue_service.get_settings",
        fake_get_settings,
    )
    monkeypatch.setattr(
        "app.services.dead_letter_queue_service.urlopen",
        fake_urlopen,
    )

    response = client.get(
        "/api/v1/dead-letter-queue/messages",
        params={"limit": 2, "truncate": 512},
    )

    assert response.status_code == 200
    assert captured_bodies == [
        {
            "count": 2,
            "ackmode": "ack_requeue_true",
            "encoding": "auto",
            "truncate": 512,
        }
    ]
    body = response.json()
    assert body["queue_name"] == "uav_dag_execution.dlq"
    assert body["enabled"] is True
    assert body["available"] is True
    assert body["items"][0]["payload"] == "execution-id-1"
    assert body["items"][0]["headers"] == {
        "x-first-death-queue": "uav_dag_execution"
    }
