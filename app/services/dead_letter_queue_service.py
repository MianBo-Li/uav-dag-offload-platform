from dataclasses import dataclass
from json import dumps, load
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.core.config import Settings, get_settings
from app.services.queue_monitoring_service import build_basic_auth_header


@dataclass(frozen=True)
class DeadLetterQueueMessage:
    payload: object | None
    payload_encoding: str | None
    exchange: str | None
    routing_key: str | None
    redelivered: bool
    message_count: int
    properties: dict[str, object]
    headers: dict[str, object]


@dataclass(frozen=True)
class DeadLetterQueuePeekResult:
    queue_name: str
    enabled: bool
    available: bool
    items: list[DeadLetterQueueMessage]
    error_message: str | None = None


class RabbitMQDeadLetterQueueService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def peek_messages(self, *, limit: int, truncate: int) -> DeadLetterQueuePeekResult:
        queue_name = self.settings.celery_task_dead_letter_queue
        if not self.settings.rabbitmq_queue_monitoring_enabled:
            return DeadLetterQueuePeekResult(
                queue_name=queue_name,
                enabled=False,
                available=False,
                items=[],
            )

        try:
            payload = self._fetch_messages(limit=limit, truncate=truncate)
        except (HTTPError, URLError, OSError, TimeoutError, ValueError) as exc:
            return DeadLetterQueuePeekResult(
                queue_name=queue_name,
                enabled=True,
                available=False,
                items=[],
                error_message=str(exc),
            )

        return DeadLetterQueuePeekResult(
            queue_name=queue_name,
            enabled=True,
            available=True,
            items=[_message_from_payload(item) for item in payload],
        )

    def _fetch_messages(self, *, limit: int, truncate: int) -> list[dict[str, object]]:
        request = Request(
            self._messages_url(),
            data=dumps(
                {
                    "count": limit,
                    "ackmode": "ack_requeue_true",
                    "encoding": "auto",
                    "truncate": truncate,
                }
            ).encode("utf-8"),
            method="POST",
        )
        request.add_header("Accept", "application/json")
        request.add_header("Content-Type", "application/json")
        request.add_header(
            "Authorization",
            build_basic_auth_header(
                self.settings.rabbitmq_management_username,
                self.settings.rabbitmq_management_password,
            ),
        )
        with urlopen(
            request,
            timeout=self.settings.rabbitmq_management_timeout_seconds,
        ) as response:
            payload = load(response)
        if not isinstance(payload, list):
            raise ValueError("RabbitMQ DLQ message payload must be a JSON list")
        if not all(isinstance(item, dict) for item in payload):
            raise ValueError("RabbitMQ DLQ message items must be JSON objects")
        return payload

    def _messages_url(self) -> str:
        base_url = self.settings.rabbitmq_management_url.rstrip("/")
        vhost = quote(self.settings.rabbitmq_management_vhost, safe="")
        queue = quote(self.settings.celery_task_dead_letter_queue, safe="")
        return f"{base_url}/queues/{vhost}/{queue}/get"


def _message_from_payload(payload: dict[str, object]) -> DeadLetterQueueMessage:
    properties = payload.get("properties")
    if not isinstance(properties, dict):
        properties = {}
    headers = properties.get("headers")
    if not isinstance(headers, dict):
        headers = {}

    return DeadLetterQueueMessage(
        payload=payload.get("payload"),
        payload_encoding=_optional_str(payload.get("payload_encoding")),
        exchange=_optional_str(payload.get("exchange")),
        routing_key=_optional_str(payload.get("routing_key")),
        redelivered=bool(payload.get("redelivered", False)),
        message_count=_int_value(payload, "message_count"),
        properties=properties,
        headers=headers,
    )


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _int_value(payload: dict[str, object], key: str) -> int:
    value = payload.get(key, 0)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0
