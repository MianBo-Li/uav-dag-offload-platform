from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import SchedulePlanStatus, SchedulerStrategyName


class ScheduleRequest(BaseModel):
    strategy_name: str = Field(
        default=SchedulerStrategyName.GREEDY.value,
        min_length=1,
        max_length=64,
    )
    options: dict[str, Any] = Field(default_factory=dict)


class SchedulePlanItemRead(BaseModel):
    id: UUID
    subtask_id: UUID
    assigned_node_id: UUID
    estimated_compute_duration_ms: int | None
    estimated_transfer_duration_ms: int | None
    estimated_energy: float | None
    decision_reason: str | None

    model_config = ConfigDict(from_attributes=True)


class SchedulePlanRead(BaseModel):
    id: UUID
    task_id: UUID
    strategy_name: SchedulerStrategyName
    status: SchedulePlanStatus
    estimated_total_duration_ms: int | None
    estimated_total_energy: float | None
    items: list[SchedulePlanItemRead]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SchedulePlanListItem(BaseModel):
    id: UUID
    task_id: UUID
    strategy_name: SchedulerStrategyName
    status: SchedulePlanStatus
    estimated_total_duration_ms: int | None
    estimated_total_energy: float | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SchedulePlanListResponse(BaseModel):
    items: list[SchedulePlanListItem]
    page: int
    page_size: int
    total: int


class ScheduleComparisonItemRead(BaseModel):
    strategy_name: SchedulerStrategyName
    feasible: bool
    failure_code: str | None
    failure_reason: str | None
    schedulable_subtask_count: int
    estimated_total_duration_ms: int | None
    estimated_total_energy: float | None
    local_assignment_count: int
    edge_assignment_count: int

    model_config = ConfigDict(from_attributes=True)


class ScheduleComparisonResponse(BaseModel):
    task_id: UUID
    items: list[ScheduleComparisonItemRead]
