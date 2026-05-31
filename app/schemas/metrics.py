from uuid import UUID

from pydantic import BaseModel

from app.domain.enums import TaskStatus


class TaskMetricsRead(BaseModel):
    task_id: UUID
    task_status: TaskStatus
    total_subtask_count: int
    success_subtask_count: int
    failed_subtask_count: int
    running_subtask_count: int
    execution_count: int
    success_execution_count: int
    failed_execution_count: int
    running_execution_count: int
    success_rate: float
    failure_rate: float
    total_execution_duration_ms: int
    average_execution_duration_ms: float | None
    local_execution_count: int
    edge_execution_count: int
    offload_rate: float
    task_elapsed_duration_ms: int | None
