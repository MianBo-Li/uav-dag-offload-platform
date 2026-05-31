from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.node import Node
from app.db.models.task import DagSubtask, DagTask, ExecutionRecord, SchedulePlan


@dataclass(frozen=True)
class MonitoringSnapshot:
    node_count: int
    task_count: int
    subtask_count: int
    schedule_plan_count: int
    execution_count: int
    execution_duration_sum_ms: int
    execution_duration_count: int
    nodes_by_type: dict[str, int]
    nodes_by_status: dict[str, int]
    tasks_by_status: dict[str, int]
    subtasks_by_status: dict[str, int]
    schedule_plans_by_status: dict[str, int]
    executions_by_status: dict[str, int]


class MonitoringRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def load_snapshot(self) -> MonitoringSnapshot:
        return MonitoringSnapshot(
            node_count=self._count(Node),
            task_count=self._count(DagTask),
            subtask_count=self._count(DagSubtask),
            schedule_plan_count=self._count(SchedulePlan),
            execution_count=self._count(ExecutionRecord),
            execution_duration_sum_ms=self._execution_duration_sum_ms(),
            execution_duration_count=self._execution_duration_count(),
            nodes_by_type=self._group_count(Node.node_type),
            nodes_by_status=self._group_count(Node.status),
            tasks_by_status=self._group_count(DagTask.status),
            subtasks_by_status=self._group_count(DagSubtask.status),
            schedule_plans_by_status=self._group_count(SchedulePlan.status),
            executions_by_status=self._group_count(ExecutionRecord.status),
        )

    def _count(self, model: type[object]) -> int:
        return self.db.scalar(select(func.count()).select_from(model)) or 0

    def _group_count(self, column) -> dict[str, int]:
        rows = self.db.execute(select(column, func.count()).group_by(column))
        return {str(key): count for key, count in rows}

    def _execution_duration_sum_ms(self) -> int:
        return (
            self.db.scalar(
                select(func.coalesce(func.sum(ExecutionRecord.duration_ms), 0))
            )
            or 0
        )

    def _execution_duration_count(self) -> int:
        return (
            self.db.scalar(
                select(func.count()).where(ExecutionRecord.duration_ms.is_not(None))
            )
            or 0
        )
