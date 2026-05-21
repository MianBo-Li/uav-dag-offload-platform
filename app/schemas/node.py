from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import NodeStatus, NodeType


class NodeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    node_type: NodeType
    cpu_capacity: float = Field(gt=0)
    memory_capacity_mb: int = Field(gt=0)
    network_address: str | None = Field(default=None, max_length=255)
    description: str | None = None


class NodeRead(BaseModel):
    id: UUID
    name: str
    node_type: NodeType
    status: NodeStatus
    cpu_capacity: float
    memory_capacity_mb: int
    network_address: str | None
    description: str | None
    last_heartbeat_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NodeListItem(BaseModel):
    id: UUID
    name: str
    node_type: NodeType
    status: NodeStatus
    cpu_capacity: float
    memory_capacity_mb: int
    last_heartbeat_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class NodeStatusCreate(BaseModel):
    battery_level: float | None = Field(default=None, ge=0, le=100)
    cpu_usage: float = Field(ge=0, le=100)
    memory_usage: float = Field(ge=0, le=100)
    network_quality: float | None = Field(default=None, ge=0, le=100)
    bandwidth_mbps: float | None = Field(default=None, ge=0)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    current_load: int | None = Field(default=None, ge=0)
    queue_length: int | None = Field(default=None, ge=0)
    reported_at: datetime


class NodeStatusRecordRead(BaseModel):
    id: UUID
    node_id: UUID
    battery_level: float | None
    cpu_usage: float
    memory_usage: float
    network_quality: float | None
    bandwidth_mbps: float | None
    latitude: float | None
    longitude: float | None
    current_load: int | None
    queue_length: int | None
    reported_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NodeStatusReportResponse(BaseModel):
    id: UUID
    node_id: UUID
    status: NodeStatus
    reported_at: datetime
    created_at: datetime


class NodeListResponse(BaseModel):
    items: list[NodeListItem]
    page: int
    page_size: int
    total: int


class NodeStatusRecordListResponse(BaseModel):
    items: list[NodeStatusRecordRead]
    page: int
    page_size: int
    total: int
