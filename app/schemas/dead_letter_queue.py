from pydantic import BaseModel


class DeadLetterQueueSnapshotResponse(BaseModel):
    queue_name: str
    enabled: bool
    available: bool
    messages: int
    messages_ready: int
    messages_unacknowledged: int
    consumers: int


class DeadLetterQueueMessageRead(BaseModel):
    payload: object | None
    payload_encoding: str | None
    exchange: str | None
    routing_key: str | None
    redelivered: bool
    message_count: int
    properties: dict[str, object]
    headers: dict[str, object]


class DeadLetterQueueMessageListResponse(BaseModel):
    queue_name: str
    enabled: bool
    available: bool
    items: list[DeadLetterQueueMessageRead]
    error_message: str | None = None
