from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import ExecutionStatus, SubtaskStatus, TaskStatus


class ExecutionStartRequest(BaseModel):
    schedule_plan_id: UUID


class ExecutionStartResponse(BaseModel):
    task_id: UUID
    schedule_plan_id: UUID
    status: TaskStatus
    execution_count: int
    execution_ids: list[UUID]


class ExecutionResultRequest(BaseModel):
    status: ExecutionStatus
    duration_ms: int | None = Field(default=None, ge=0)
    output_summary: str | None = None
    failure_reason: str | None = None


class ExecutionResultResponse(BaseModel):
    execution_id: UUID
    subtask_status: SubtaskStatus
    task_status: TaskStatus
    accepted: bool


class ExecutionRecordRead(BaseModel):
    id: UUID
    task_id: UUID
    subtask_id: UUID
    node_id: UUID
    plan_item_id: UUID | None
    attempt: int
    status: ExecutionStatus
    started_at: datetime | None
    finished_at: datetime | None
    duration_ms: int | None
    output_summary: str | None
    failure_reason: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExecutionRecordListResponse(BaseModel):
    items: list[ExecutionRecordRead]
    page: int
    page_size: int
    total: int
