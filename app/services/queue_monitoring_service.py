from dataclasses import dataclass
from json import load
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class QueueMonitoringSnapshot:
    queue_name: str
    enabled: bool
    available: bool
    messages: int
    messages_ready: int
    messages_unacknowledged: int
    consumers: int


class RabbitMQQueueMonitoringService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def load_snapshot(self) -> QueueMonitoringSnapshot:
        return self._load_snapshot(self.settings.celery_task_default_queue)

    def load_snapshots(self) -> list[QueueMonitoringSnapshot]:
        return [self._load_snapshot(queue_name) for queue_name in self._queue_names()]

    def _load_snapshot(self, queue_name: str) -> QueueMonitoringSnapshot:
        if not self.settings.rabbitmq_queue_monitoring_enabled:
            return _empty_snapshot(queue_name, enabled=False)

        try:
            payload = self._fetch_queue_payload(queue_name)
        except (HTTPError, URLError, OSError, TimeoutError, ValueError):
            return _empty_snapshot(queue_name, enabled=True)

        return QueueMonitoringSnapshot(
            queue_name=queue_name,
            enabled=True,
            available=True,
            messages=_int_value(payload, "messages"),
            messages_ready=_int_value(payload, "messages_ready"),
            messages_unacknowledged=_int_value(payload, "messages_unacknowledged"),
            consumers=_int_value(payload, "consumers"),
        )

    def _queue_names(self) -> list[str]:
        queue_names = [
            self.settings.celery_task_default_queue,
            self.settings.celery_task_dead_letter_queue,
        ]
        return list(dict.fromkeys(queue_names))

    def _fetch_queue_payload(self, queue_name: str) -> dict[str, object]:
        url = self._queue_url(queue_name)
        request = Request(url)
        request.add_header("Accept", "application/json")
        request.add_header(
            "Authorization",
            _basic_auth_header(
                self.settings.rabbitmq_management_username,
                self.settings.rabbitmq_management_password,
            ),
        )
        with urlopen(
            request,
            timeout=self.settings.rabbitmq_management_timeout_seconds,
        ) as response:
            payload = load(response)
        if not isinstance(payload, dict):
            raise ValueError("RabbitMQ queue payload must be a JSON object")
        return payload

    def _queue_url(self, queue_name: str) -> str:
        base_url = self.settings.rabbitmq_management_url.rstrip("/")
        vhost = quote(self.settings.rabbitmq_management_vhost, safe="")
        queue = quote(queue_name, safe="")
        return f"{base_url}/queues/{vhost}/{queue}"


def _empty_snapshot(queue_name: str, *, enabled: bool) -> QueueMonitoringSnapshot:
    return QueueMonitoringSnapshot(
        queue_name=queue_name,
        enabled=enabled,
        available=False,
        messages=0,
        messages_ready=0,
        messages_unacknowledged=0,
        consumers=0,
    )


def _int_value(payload: dict[str, object], key: str) -> int:
    value = payload.get(key, 0)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


def _basic_auth_header(username: str, password: str) -> str:
    import base64

    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"
