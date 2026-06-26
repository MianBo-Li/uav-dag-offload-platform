from json import dumps, loads

from app.core.config import Settings
from app.services.dead_letter_flow_verifier import RabbitMQDeadLetterFlowVerifier


class FakeRabbitMQResponse:
    def __init__(self, payload: bytes = b"") -> None:
        self.payload = payload

    def __enter__(self) -> "FakeRabbitMQResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


def _settings(**overrides: object) -> Settings:
    values = {
        "rabbitmq_management_url": "http://rabbitmq:15672/api",
        "rabbitmq_management_username": "guest",
        "rabbitmq_management_password": "guest",
        "rabbitmq_management_vhost": "/",
        "rabbitmq_management_timeout_seconds": 1.0,
        "celery_task_default_queue": "uav_dag_execution",
        "celery_task_default_exchange": "uav_dag_execution",
        "celery_task_default_routing_key": "uav_dag_execution",
        "celery_task_dead_letter_exchange": "uav_dag_execution.dlx",
        "celery_task_dead_letter_routing_key": "uav_dag_execution.dead",
        "celery_task_dead_letter_queue": "uav_dag_execution.dlq",
    }
    values.update(overrides)
    return Settings(**values)


def test_dead_letter_flow_verifier_rejects_probe_and_finds_it_in_dlq(monkeypatch) -> None:
    requests: list[tuple[str, str, dict[str, object] | None]] = []
    probe_id = ""

    def fake_urlopen(request, timeout: float):
        nonlocal probe_id
        body = loads(request.data.decode("utf-8")) if request.data else None
        requests.append((request.get_method(), request.full_url, body))

        if request.get_method() == "GET":
            return FakeRabbitMQResponse(
                dumps(
                    {
                        "arguments": {
                            "x-dead-letter-exchange": "uav_dag_execution.dlx",
                            "x-dead-letter-routing-key": "uav_dag_execution.dead",
                        }
                    }
                ).encode("utf-8")
            )
        if request.full_url.endswith("/publish"):
            assert body is not None
            probe_payload = loads(str(body["payload"]))
            probe_id = probe_payload["probe_id"]
            return FakeRabbitMQResponse(b'{"routed": true}')
        if request.full_url.endswith("/get"):
            assert body is not None
            if body["ackmode"] == "reject_requeue_false":
                return FakeRabbitMQResponse(
                    dumps([{"payload": {"probe_id": probe_id}}]).encode("utf-8")
                )
            return FakeRabbitMQResponse(
                dumps(
                    [
                        {
                            "payload": {"probe_id": probe_id},
                            "message_count": 0,
                            "properties": {
                                "headers": {"x-uav-dag-dlq-probe-id": probe_id}
                            },
                        }
                    ]
                ).encode("utf-8")
            )
        return FakeRabbitMQResponse()

    monkeypatch.setattr(
        "app.services.dead_letter_flow_verifier.urlopen",
        fake_urlopen,
    )

    result = RabbitMQDeadLetterFlowVerifier(_settings()).verify_probe_flow(
        timeout_seconds=0.1,
        poll_interval_seconds=0.0,
    )

    assert result.error_message is None
    assert result.main_queue_dead_letter_configured is True
    assert result.published is True
    assert result.rejected is True
    assert result.found_in_dlq is True
    assert result.dlq_message_count == 1
    assert result.probe_id == probe_id

    request_bodies = [body for _, _, body in requests if body is not None]
    assert any(
        body.get("ackmode") == "reject_requeue_false" for body in request_bodies
    )
    assert any(body.get("ackmode") == "ack_requeue_true" for body in request_bodies)
    assert any(body.get("routing_key") == result.probe_routing_key for body in request_bodies)


def test_dead_letter_flow_verifier_reports_missing_main_queue_dlq_config(
    monkeypatch,
) -> None:
    probe_id = ""

    def fake_urlopen(request, timeout: float):
        nonlocal probe_id
        if request.get_method() == "GET":
            return FakeRabbitMQResponse(dumps({"arguments": {}}).encode("utf-8"))
        if request.full_url.endswith("/publish"):
            body = loads(request.data.decode("utf-8"))
            probe_id = loads(str(body["payload"]))["probe_id"]
            return FakeRabbitMQResponse(b'{"routed": true}')
        if request.full_url.endswith("/get"):
            body = loads(request.data.decode("utf-8"))
            if body["ackmode"] == "reject_requeue_false":
                return FakeRabbitMQResponse(
                    dumps([{"payload": {"probe_id": probe_id}}]).encode("utf-8")
                )
            return FakeRabbitMQResponse(
                dumps([{"payload": {"probe_id": probe_id}}]).encode("utf-8")
            )
        return FakeRabbitMQResponse()

    monkeypatch.setattr(
        "app.services.dead_letter_flow_verifier.urlopen",
        fake_urlopen,
    )

    result = RabbitMQDeadLetterFlowVerifier(_settings()).verify_probe_flow(
        timeout_seconds=0.1,
        poll_interval_seconds=0.0,
    )

    assert result.main_queue_dead_letter_configured is False
    assert result.published is True
    assert result.rejected is True
    assert result.found_in_dlq is True
