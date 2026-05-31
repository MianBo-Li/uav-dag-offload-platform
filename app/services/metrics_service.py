from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.enums import ExecutionStatus, NodeType, SubtaskStatus
from app.repositories.execution_repository import ExecutionRepository
from app.schemas.metrics import TaskMetricsRead
from app.services.task_service import TaskService


class MetricsService:
    def __init__(self, db: Session) -> None:
        self.task_service = TaskService(db)
        self.execution_repository = ExecutionRepository(db)

    def get_task_metrics(self, task_id: UUID) -> TaskMetricsRead:
        task = self.task_service.get_task(task_id)
        records = self.execution_repository.list_all_by_task(task_id)
        node_type_counts = self.execution_repository.count_by_node_type(task_id)

        execution_count = len(records)
        success_execution_count = sum(
            record.status == ExecutionStatus.SUCCESS for record in records
        )
        failed_execution_count = sum(
            record.status
            in {
                ExecutionStatus.FAILED,
                ExecutionStatus.TIMEOUT,
                ExecutionStatus.CANCELED,
            }
            for record in records
        )
        running_execution_count = sum(
            record.status == ExecutionStatus.RUNNING for record in records
        )
        durations = [
            record.duration_ms
            for record in records
            if record.duration_ms is not None
        ]
        total_execution_duration_ms = sum(durations)

        return TaskMetricsRead(
            task_id=task.id,
            task_status=task.status,
            total_subtask_count=len(task.subtasks),
            success_subtask_count=sum(
                subtask.status == SubtaskStatus.SUCCESS for subtask in task.subtasks
            ),
            failed_subtask_count=sum(
                subtask.status == SubtaskStatus.FAILED for subtask in task.subtasks
            ),
            running_subtask_count=sum(
                subtask.status == SubtaskStatus.RUNNING for subtask in task.subtasks
            ),
            execution_count=execution_count,
            success_execution_count=success_execution_count,
            failed_execution_count=failed_execution_count,
            running_execution_count=running_execution_count,
            success_rate=_rate(success_execution_count, execution_count),
            failure_rate=_rate(failed_execution_count, execution_count),
            total_execution_duration_ms=total_execution_duration_ms,
            average_execution_duration_ms=(
                round(total_execution_duration_ms / len(durations), 4)
                if durations
                else None
            ),
            local_execution_count=node_type_counts.get(NodeType.UAV, 0),
            edge_execution_count=node_type_counts.get(NodeType.EDGE, 0),
            offload_rate=_rate(node_type_counts.get(NodeType.EDGE, 0), execution_count),
            task_elapsed_duration_ms=_elapsed_ms(task.started_at, task.finished_at),
        )


def _rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)


def _elapsed_ms(started_at: datetime | None, finished_at: datetime | None) -> int | None:
    if started_at is None or finished_at is None:
        return None
    return round((finished_at - started_at).total_seconds() * 1000)
