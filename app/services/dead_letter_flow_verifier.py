from dataclasses import dataclass
from json import dumps, loads
from time import monotonic, sleep
from uuid import uuid4
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.core.config import Settings, get_settings
from app.services.queue_monitoring_service import build_basic_auth_header


@dataclass(frozen=True)
class DeadLetterFlowVerificationResult:
    probe_id: str
    probe_queue: str
    probe_routing_key: str
    main_queue_dead_letter_configured: bool
    published: bool
    rejected: bool
    found_in_dlq: bool
    dlq_message_count: int
    error_message: str | None = None


class RabbitMQDeadLetterFlowVerifier:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def verify_probe_flow(
        self,
        *,
        timeout_seconds: float = 10.0,
        poll_interval_seconds: float = 0.5,
    ) -> DeadLetterFlowVerificationResult:
        probe_id = f"dlq-probe-{uuid4()}"
        probe_queue = f"{self.settings.celery_task_default_queue}.probe.{probe_id}"
        probe_routing_key = f"{self.settings.celery_task_default_routing_key}.probe.{probe_id}"
        main_queue_dead_letter_configured = False
        published = False
        rejected = False
        found_in_dlq = False
        dlq_message_count = 0
        error_message: str | None = None

        try:
            main_queue_dead_letter_configured = self._main_queue_has_dead_letter_config()
            self._declare_dead_letter_exchange()
            self._declare_dead_letter_queue()
            self._bind_dead_letter_queue()
            self._declare_probe_queue(probe_queue)
            self._bind_probe_queue(probe_queue, probe_routing_key)
            published = self._publish_probe_message(
                probe_id=probe_id,
                routing_key=probe_routing_key,
            )
            rejected = self._reject_probe_message(probe_queue)
            found_in_dlq, dlq_message_count = self._wait_for_probe_in_dlq(
                probe_id=probe_id,
                timeout_seconds=timeout_seconds,
                poll_interval_seconds=poll_interval_seconds,
            )
        except (HTTPError, URLError, OSError, TimeoutError, ValueError) as exc:
            error_message = str(exc)
        finally:
            try:
                self._delete_probe_queue(probe_queue)
            except (HTTPError, URLError, OSError, TimeoutError, ValueError):
                pass

        return DeadLetterFlowVerificationResult(
            probe_id=probe_id,
            probe_queue=probe_queue,
            probe_routing_key=probe_routing_key,
            main_queue_dead_letter_configured=main_queue_dead_letter_configured,
            published=published,
            rejected=rejected,
            found_in_dlq=found_in_dlq,
            dlq_message_count=dlq_message_count,
            error_message=error_message,
        )

    def _main_queue_has_dead_letter_config(self) -> bool:
        payload = self._request_json(
            "GET",
            self._queue_url(self.settings.celery_task_default_queue),
        )
        if not isinstance(payload, dict):
            raise ValueError("RabbitMQ queue detail payload must be a JSON object")
        arguments = payload.get("arguments")
        if not isinstance(arguments, dict):
            return False
        return (
            arguments.get("x-dead-letter-exchange")
            == self.settings.celery_task_dead_letter_exchange
            and arguments.get("x-dead-letter-routing-key")
            == self.settings.celery_task_dead_letter_routing_key
        )

    def _declare_probe_queue(self, probe_queue: str) -> None:
        self._request_json(
            "PUT",
            self._queue_url(probe_queue),
            {
                "durable": False,
                "auto_delete": True,
                "arguments": {
                    "x-dead-letter-exchange": self.settings.celery_task_dead_letter_exchange,
                    "x-dead-letter-routing-key": self.settings.celery_task_dead_letter_routing_key,
                },
            },
        )

    def _declare_dead_letter_exchange(self) -> None:
        self._request_json(
            "PUT",
            self._exchange_url(self.settings.celery_task_dead_letter_exchange),
            {
                "type": "direct",
                "durable": True,
                "auto_delete": False,
                "internal": False,
                "arguments": {},
            },
        )

    def _declare_dead_letter_queue(self) -> None:
        self._request_json(
            "PUT",
            self._queue_url(self.settings.celery_task_dead_letter_queue),
            {
                "durable": True,
                "auto_delete": False,
                "arguments": {},
            },
        )

    def _bind_dead_letter_queue(self) -> None:
        self._request_json(
            "POST",
            self._binding_url(
                exchange_name=self.settings.celery_task_dead_letter_exchange,
                queue_name=self.settings.celery_task_dead_letter_queue,
            ),
            {"routing_key": self.settings.celery_task_dead_letter_routing_key},
        )

    def _bind_probe_queue(self, probe_queue: str, routing_key: str) -> None:
        self._request_json(
            "POST",
            self._binding_url(
                exchange_name=self.settings.celery_task_default_exchange,
                queue_name=probe_queue,
            ),
            {"routing_key": routing_key},
        )

    def _publish_probe_message(self, *, probe_id: str, routing_key: str) -> bool:
        payload = self._request_json(
            "POST",
            self._exchange_publish_url(),
            {
                "properties": {
                    "delivery_mode": 2,
                    "content_type": "application/json",
                    "headers": {"x-uav-dag-dlq-probe-id": probe_id},
                },
                "routing_key": routing_key,
                "payload": dumps(
                    {
                        "probe_id": probe_id,
                        "source": "uav-dag-offload-platform",
                    }
                ),
                "payload_encoding": "string",
            },
        )
        if not isinstance(payload, dict):
            raise ValueError("RabbitMQ publish payload must be a JSON object")
        return bool(payload.get("routed"))

    def _reject_probe_message(self, probe_queue: str) -> bool:
        payload = self._get_messages(
            queue_name=probe_queue,
            count=1,
            ackmode="reject_requeue_false",
            truncate=10_000,
        )
        return bool(payload)

    def _wait_for_probe_in_dlq(
        self,
        *,
        probe_id: str,
        timeout_seconds: float,
        poll_interval_seconds: float,
    ) -> tuple[bool, int]:
        deadline = monotonic() + timeout_seconds
        last_message_count = 0

        while True:
            messages = self._get_messages(
                queue_name=self.settings.celery_task_dead_letter_queue,
                count=50,
                ackmode="ack_requeue_true",
                truncate=50_000,
            )
            if messages:
                last_message_count = _int_value(messages[0], "message_count") + len(messages)
            if any(_contains_probe_id(message, probe_id) for message in messages):
                return True, last_message_count
            if monotonic() >= deadline:
                return False, last_message_count
            sleep(poll_interval_seconds)

    def _get_messages(
        self,
        *,
        queue_name: str,
        count: int,
        ackmode: str,
        truncate: int,
    ) -> list[dict[str, object]]:
        payload = self._request_json(
            "POST",
            f"{self._queue_url(queue_name)}/get",
            {
                "count": count,
                "ackmode": ackmode,
                "encoding": "auto",
                "truncate": truncate,
            },
        )
        if not isinstance(payload, list):
            raise ValueError("RabbitMQ get payload must be a JSON list")
        if not all(isinstance(item, dict) for item in payload):
            raise ValueError("RabbitMQ get message items must be JSON objects")
        return payload

    def _request_json(
        self,
        method: str,
        url: str,
        body: dict[str, object] | None = None,
    ) -> object:
        data = None if body is None else dumps(body).encode("utf-8")
        request = Request(url, data=data, method=method)
        request.add_header("Accept", "application/json")
        request.add_header(
            "Authorization",
            build_basic_auth_header(
                self.settings.rabbitmq_management_username,
                self.settings.rabbitmq_management_password,
            ),
        )
        if body is not None:
            request.add_header("Content-Type", "application/json")
        with urlopen(
            request,
            timeout=self.settings.rabbitmq_management_timeout_seconds,
        ) as response:
            raw_payload = response.read()
        if not raw_payload:
            return None
        return loads(raw_payload.decode("utf-8"))

    def _queue_url(self, queue_name: str) -> str:
        return f"{self._base_url()}/queues/{self._vhost()}/{quote(queue_name, safe='')}"

    def _binding_url(self, *, exchange_name: str, queue_name: str) -> str:
        exchange = quote(exchange_name, safe="")
        queue = quote(queue_name, safe="")
        return f"{self._base_url()}/bindings/{self._vhost()}/e/{exchange}/q/{queue}"

    def _exchange_url(self, exchange_name: str) -> str:
        exchange = quote(exchange_name, safe="")
        return f"{self._base_url()}/exchanges/{self._vhost()}/{exchange}"

    def _exchange_publish_url(self) -> str:
        exchange = quote(self.settings.celery_task_default_exchange, safe="")
        return f"{self._base_url()}/exchanges/{self._vhost()}/{exchange}/publish"

    def _delete_probe_queue(self, queue_name: str) -> None:
        self._request_json("DELETE", self._queue_url(queue_name))

    def _base_url(self) -> str:
        return self.settings.rabbitmq_management_url.rstrip("/")

    def _vhost(self) -> str:
        return quote(self.settings.rabbitmq_management_vhost, safe="")


def _contains_probe_id(message: dict[str, object], probe_id: str) -> bool:
    return probe_id in dumps(message, ensure_ascii=False, default=str)


def _int_value(payload: dict[str, object], key: str) -> int:
    value = payload.get(key, 0)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0
