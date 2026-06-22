from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import ExecutionStatus, SubtaskStatus, TaskStatus


class ExecutionSimulationOptions(BaseModel):
    result_status: ExecutionStatus = ExecutionStatus.SUCCESS
    duration_ms: int | None = Field(default=None, ge=0)
    output_summary: str | None = None
    failure_reason: str | None = None

    @field_validator("result_status")
    @classmethod
    def result_status_must_be_terminal(
        cls,
        value: ExecutionStatus,
    ) -> ExecutionStatus:
        if value == ExecutionStatus.RUNNING:
            raise ValueError("Simulated result status must be terminal")
        return value


class ExecutionStartRequest(BaseModel):
    schedule_plan_id: UUID
    simulation: ExecutionSimulationOptions | None = None


class ExecutionStartResponse(BaseModel):
    task_id: UUID
    schedule_plan_id: UUID
    status: TaskStatus
    execution_count: int
    execution_ids: list[UUID]
    queued_count: int = 0


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
    celery_task_id: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExecutionRecordListResponse(BaseModel):
    items: list[ExecutionRecordRead]
    page: int
    page_size: int
    total: int
