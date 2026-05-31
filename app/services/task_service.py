from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models.task import DagDependency, DagSubtask, DagTask
from app.domain.dag import validate_dag
from app.domain.enums import SubtaskStatus, TaskStatus
from app.domain.state_machine import ensure_transition_allowed
from app.repositories.task_repository import TaskRepository
from app.schemas.task import DagTaskCancelRequest, DagTaskCreate


class TaskService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = TaskRepository(db)

    def create_task(self, data: DagTaskCreate) -> DagTask:
        subtask_ids = [subtask.external_id for subtask in data.subtasks]
        dependencies = [
            (dependency.from_, dependency.to) for dependency in data.dependencies
        ]
        try:
            validate_dag(subtask_ids, dependencies)
        except ValueError as exc:
            raise AppError(
                code="DAG_VALIDATION_FAILED",
                message=str(exc),
                status_code=400,
                details={"reason": str(exc)},
            ) from exc

        successor_ids = {successor for _, successor in dependencies}

        task = DagTask(
            name=data.name,
            status=TaskStatus.PENDING,
            priority=data.priority,
            deadline_at=data.deadline_at,
            submitted_by=data.submitted_by,
            metadata_json=data.metadata,
        )
        task.subtasks = [
            DagSubtask(
                external_id=subtask.external_id,
                name=subtask.name,
                status=(
                    SubtaskStatus.WAITING
                    if subtask.external_id in successor_ids
                    else SubtaskStatus.READY
                ),
                execution_constraint=subtask.execution_constraint,
                compute_load=subtask.compute_load,
                input_data_size_mb=subtask.input_data_size_mb,
                output_data_size_mb=subtask.output_data_size_mb,
                max_retries=subtask.max_retries,
                retry_count=0,
                metadata_json=subtask.metadata,
            )
            for subtask in data.subtasks
        ]

        saved_task = self.repository.create(task)
        subtask_map = {subtask.external_id: subtask for subtask in saved_task.subtasks}
        saved_task.dependencies = [
            DagDependency(
                task_id=saved_task.id,
                predecessor_subtask_id=subtask_map[predecessor].id,
                successor_subtask_id=subtask_map[successor].id,
            )
            for predecessor, successor in dependencies
        ]
        self.db.flush()
        self.db.refresh(saved_task)
        return saved_task

    def get_task(self, task_id: UUID) -> DagTask:
        task = self.repository.get_by_id(task_id)
        if task is None:
            raise AppError(
                code="TASK_NOT_FOUND",
                message="Task not found",
                status_code=404,
                details={"task_id": str(task_id)},
            )
        return task

    def list_tasks(
        self,
        status: TaskStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[list[DagTask], int]:
        return self.repository.list_tasks(status, page, page_size)

    def list_subtasks(
        self,
        task_id: UUID,
        status: SubtaskStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[list[DagSubtask], int]:
        self.get_task(task_id)
        return self.repository.list_subtasks(task_id, status, page, page_size)

    def cancel_task(self, task_id: UUID, data: DagTaskCancelRequest) -> DagTask:
        task = self.get_task(task_id)
        try:
            ensure_transition_allowed(task.status, TaskStatus.CANCELED)
        except ValueError as exc:
            raise AppError(
                code="TASK_STATE_CONFLICT",
                message=str(exc),
                status_code=409,
                details={
                    "task_id": str(task_id),
                    "current_status": task.status,
                    "target_status": TaskStatus.CANCELED,
                },
            ) from exc

        task.status = TaskStatus.CANCELED
        task.failure_reason = data.reason
        self.db.flush()
        self.db.refresh(task)
        return task
