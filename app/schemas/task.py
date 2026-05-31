from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import SubtaskExecutionConstraint, SubtaskStatus, TaskStatus


class SubtaskCreate(BaseModel):
    external_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    compute_load: float = Field(gt=0)
    input_data_size_mb: float = Field(ge=0)
    output_data_size_mb: float = Field(ge=0)
    execution_constraint: SubtaskExecutionConstraint = (
        SubtaskExecutionConstraint.OFFLOADABLE
    )
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


class DagTaskCancelRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=255)


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


class DagSubtaskRead(BaseModel):
    id: UUID
    external_id: str
    name: str
    status: SubtaskStatus
    execution_constraint: SubtaskExecutionConstraint
    compute_load: float
    input_data_size_mb: float
    output_data_size_mb: float
    retry_count: int
    max_retries: int

    model_config = ConfigDict(from_attributes=True)


class DagDependencyRead(BaseModel):
    from_: str = Field(alias="from")
    to: str

    model_config = ConfigDict(populate_by_name=True)


class DagTaskDetailRead(BaseModel):
    id: UUID
    name: str
    status: TaskStatus
    priority: int
    deadline_at: datetime | None
    subtasks: list[DagSubtaskRead]
    dependencies: list[DagDependencyRead]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DagSubtaskListResponse(BaseModel):
    items: list[DagSubtaskRead]
    page: int
    page_size: int
    total: int


class DagTaskCancelResponse(BaseModel):
    task_id: UUID
    status: TaskStatus
    reason: str | None
    updated_at: datetime
