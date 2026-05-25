from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import TaskStatus


class SubtaskCreate(BaseModel):
    external_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    compute_load: float = Field(gt=0)
    input_data_size_mb: float = Field(ge=0)
    output_data_size_mb: float = Field(ge=0)
    max_retries: int = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DependencyCreate(BaseModel):
    from_: str = Field(alias="from", min_length=1, max_length=64)
    to: str = Field(min_length=1, max_length=64)


class DagTaskCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    priority: int = Field(default=0, ge=0)
    deadline_at: datetime | None = None
    submitted_by: str | None = Field(default=None, max_length=128)
    subtasks: list[SubtaskCreate] = Field(min_length=1)
    dependencies: list[DependencyCreate] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DagTaskRead(BaseModel):
    id: UUID
    name: str
    status: TaskStatus
    priority: int
    deadline_at: datetime | None
    subtask_count: int
    dependency_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DagTaskListItem(BaseModel):
    id: UUID
    name: str
    status: TaskStatus
    priority: int
    deadline_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DagTaskListResponse(BaseModel):
    items: list[DagTaskListItem]
    page: int
    page_size: int
    total: int
