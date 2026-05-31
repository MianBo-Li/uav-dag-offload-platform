from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models.task import ExecutionRecord, SchedulePlan
from app.domain.enums import (
    ExecutionStatus,
    SchedulePlanStatus,
    SubtaskStatus,
    TaskStatus,
)
from app.domain.state_machine import ensure_transition_allowed
from app.repositories.execution_repository import ExecutionRepository
from app.repositories.schedule_repository import ScheduleRepository
from app.services.task_service import TaskService


@dataclass(frozen=True)
class ExecutionStartResult:
    task_id: UUID
    schedule_plan_id: UUID
    status: TaskStatus
    execution_count: int
    execution_ids: list[UUID]


@dataclass(frozen=True)
class ExecutionResult:
    execution_id: UUID
    subtask_status: SubtaskStatus
    task_status: TaskStatus
    accepted: bool


class ExecutionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.task_service = TaskService(db)
        self.schedule_repository = ScheduleRepository(db)
        self.execution_repository = ExecutionRepository(db)

    def start_execution(
        self,
        task_id: UUID,
        schedule_plan_id: UUID,
    ) -> ExecutionStartResult:
        task = self.task_service.get_task(task_id)
        self._ensure_task_can_run(task.status, task_id)

        plan = self._get_plan(schedule_plan_id)
        if plan.task_id != task_id:
            raise AppError(
                code="SCHEDULE_PLAN_TASK_MISMATCH",
                message="Schedule plan does not belong to task",
                status_code=400,
                details={
                    "task_id": str(task_id),
                    "schedule_plan_id": str(schedule_plan_id),
                },
            )
        self._ensure_plan_can_apply(plan)

        if not plan.items:
            raise AppError(
                code="NO_EXECUTABLE_PLAN_ITEM",
                message="Schedule plan has no executable items",
                status_code=409,
                details={"schedule_plan_id": str(schedule_plan_id)},
            )

        now = datetime.now(UTC)
        records: list[ExecutionRecord] = []
        for item in plan.items:
            subtask = item.subtask
            self._move_subtask_to_running(subtask.status, subtask.id)
            subtask.status = SubtaskStatus.DISPATCHED
            subtask.status = SubtaskStatus.RUNNING
            subtask.started_at = now

            records.append(
                ExecutionRecord(
                    task_id=task_id,
                    subtask_id=item.subtask_id,
                    node_id=item.assigned_node_id,
                    plan_item_id=item.id,
                    attempt=subtask.retry_count + 1,
                    status=ExecutionStatus.RUNNING,
                    started_at=now,
                )
            )

        plan.status = SchedulePlanStatus.APPLIED
        plan.applied_at = now
        task.status = TaskStatus.RUNNING
        task.started_at = task.started_at or now

        saved_records = self.execution_repository.create_many(records)
        self.db.flush()
        return ExecutionStartResult(
            task_id=task_id,
            schedule_plan_id=schedule_plan_id,
            status=task.status,
            execution_count=len(saved_records),
            execution_ids=[record.id for record in saved_records],
        )

    def list_task_executions(
        self,
        task_id: UUID,
        status: ExecutionStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[list[ExecutionRecord], int]:
        self.task_service.get_task(task_id)
        return self.execution_repository.list_by_task(task_id, status, page, page_size)

    def report_result(
        self,
        execution_id: UUID,
        status: ExecutionStatus,
        duration_ms: int | None = None,
        output_summary: str | None = None,
        failure_reason: str | None = None,
    ) -> ExecutionResult:
        record = self.execution_repository.get_by_id(execution_id)
        if record is None:
            raise AppError(
                code="EXECUTION_NOT_FOUND",
                message="Execution record not found",
                status_code=404,
                details={"execution_id": str(execution_id)},
            )

        # Idempotency guard: duplicate or late results must not advance state twice.
        if record.status != ExecutionStatus.RUNNING:
            return ExecutionResult(
                execution_id=record.id,
                subtask_status=record.subtask.status,
                task_status=record.task.status,
                accepted=False,
            )

        now = datetime.now(UTC)
        self._ensure_execution_can_finish(record.status, status, record.id)
        record.status = status
        record.finished_at = now
        record.duration_ms = duration_ms
        record.output_summary = output_summary
        record.failure_reason = failure_reason

        subtask = record.subtask
        task = self.task_service.get_task(record.task_id)
        if status == ExecutionStatus.SUCCESS:
            self._move_subtask_to_terminal(
                subtask.status,
                SubtaskStatus.SUCCESS,
                subtask.id,
            )
            subtask.status = SubtaskStatus.SUCCESS
            subtask.finished_at = now
            self._unlock_successors(task, subtask.id)
            if all(item.status == SubtaskStatus.SUCCESS for item in task.subtasks):
                self._move_task_to_terminal(task.status, TaskStatus.SUCCESS, task.id)
                task.status = TaskStatus.SUCCESS
                task.finished_at = now
        elif status in {
            ExecutionStatus.FAILED,
            ExecutionStatus.TIMEOUT,
            ExecutionStatus.CANCELED,
        }:
            if self._can_retry_subtask(status, subtask.retry_count, subtask.max_retries):
                self._move_subtask_to_retry_ready(subtask.status, subtask.id)
                subtask.status = SubtaskStatus.READY
                subtask.retry_count += 1
                subtask.started_at = None
                subtask.finished_at = None
                subtask.failure_reason = failure_reason
            else:
                self._move_subtask_to_terminal(
                    subtask.status,
                    SubtaskStatus.FAILED,
                    subtask.id,
                )
                subtask.status = SubtaskStatus.FAILED
                subtask.finished_at = now
                subtask.failure_reason = failure_reason
                self._move_task_to_terminal(task.status, TaskStatus.FAILED, task.id)
                task.status = TaskStatus.FAILED
                task.failure_reason = failure_reason
                task.finished_at = now

        self.db.flush()
        return ExecutionResult(
            execution_id=record.id,
            subtask_status=subtask.status,
            task_status=task.status,
            accepted=True,
        )

    def _get_plan(self, schedule_plan_id: UUID) -> SchedulePlan:
        plan = self.schedule_repository.get_by_id(schedule_plan_id)
        if plan is None:
            raise AppError(
                code="SCHEDULE_PLAN_NOT_FOUND",
                message="Schedule plan not found",
                status_code=404,
                details={"schedule_plan_id": str(schedule_plan_id)},
            )
        return plan

    @staticmethod
    def _ensure_execution_can_finish(
        current_status: ExecutionStatus,
        target_status: ExecutionStatus,
        execution_id: UUID,
    ) -> None:
        try:
            ensure_transition_allowed(current_status, target_status)
        except ValueError as exc:
            raise AppError(
                code="EXECUTION_STATE_CONFLICT",
                message=str(exc),
                status_code=409,
                details={
                    "execution_id": str(execution_id),
                    "current_status": current_status,
                    "target_status": target_status,
                },
            ) from exc

    @staticmethod
    def _move_subtask_to_terminal(
        current_status: SubtaskStatus,
        target_status: SubtaskStatus,
        subtask_id: UUID,
    ) -> None:
        try:
            ensure_transition_allowed(current_status, target_status)
        except ValueError as exc:
            raise AppError(
                code="SUBTASK_STATE_CONFLICT",
                message=str(exc),
                status_code=409,
                details={
                    "subtask_id": str(subtask_id),
                    "current_status": current_status,
                    "target_status": target_status,
                },
            ) from exc

    @staticmethod
    def _move_subtask_to_retry_ready(
        current_status: SubtaskStatus,
        subtask_id: UUID,
    ) -> None:
        try:
            ensure_transition_allowed(current_status, SubtaskStatus.FAILED)
            ensure_transition_allowed(SubtaskStatus.FAILED, SubtaskStatus.RETRYING)
            ensure_transition_allowed(SubtaskStatus.RETRYING, SubtaskStatus.READY)
        except ValueError as exc:
            raise AppError(
                code="SUBTASK_STATE_CONFLICT",
                message=str(exc),
                status_code=409,
                details={
                    "subtask_id": str(subtask_id),
                    "current_status": current_status,
                    "target_status": SubtaskStatus.READY,
                },
            ) from exc

    @staticmethod
    def _can_retry_subtask(
        status: ExecutionStatus,
        retry_count: int,
        max_retries: int,
    ) -> bool:
        return status in {ExecutionStatus.FAILED, ExecutionStatus.TIMEOUT} and (
            retry_count < max_retries
        )

    @staticmethod
    def _move_task_to_terminal(
        current_status: TaskStatus,
        target_status: TaskStatus,
        task_id: UUID,
    ) -> None:
        try:
            ensure_transition_allowed(current_status, target_status)
        except ValueError as exc:
            raise AppError(
                code="TASK_STATE_CONFLICT",
                message=str(exc),
                status_code=409,
                details={
                    "task_id": str(task_id),
                    "current_status": current_status,
                    "target_status": target_status,
                },
            ) from exc

    @staticmethod
    def _unlock_successors(task, completed_subtask_id: UUID) -> None:
        subtask_by_id = {subtask.id: subtask for subtask in task.subtasks}
        for dependency in task.dependencies:
            if dependency.predecessor_subtask_id != completed_subtask_id:
                continue

            successor = subtask_by_id[dependency.successor_subtask_id]
            if successor.status != SubtaskStatus.WAITING:
                continue

            predecessor_ids = [
                item.predecessor_subtask_id
                for item in task.dependencies
                if item.successor_subtask_id == successor.id
            ]
            if all(
                subtask_by_id[predecessor_id].status == SubtaskStatus.SUCCESS
                for predecessor_id in predecessor_ids
            ):
                ensure_transition_allowed(successor.status, SubtaskStatus.READY)
                successor.status = SubtaskStatus.READY

    @staticmethod
    def _ensure_task_can_run(status: TaskStatus, task_id: UUID) -> None:
        if status == TaskStatus.RUNNING:
            return

        try:
            ensure_transition_allowed(status, TaskStatus.RUNNING)
        except ValueError as exc:
            raise AppError(
                code="TASK_STATE_CONFLICT",
                message=str(exc),
                status_code=409,
                details={
                    "task_id": str(task_id),
                    "current_status": status,
                    "target_status": TaskStatus.RUNNING,
                },
            ) from exc

    @staticmethod
    def _ensure_plan_can_apply(plan: SchedulePlan) -> None:
        try:
            ensure_transition_allowed(plan.status, SchedulePlanStatus.APPLIED)
        except ValueError as exc:
            raise AppError(
                code="SCHEDULE_PLAN_STATE_CONFLICT",
                message=str(exc),
                status_code=409,
                details={
                    "schedule_plan_id": str(plan.id),
                    "current_status": plan.status,
                    "target_status": SchedulePlanStatus.APPLIED,
                },
            ) from exc

    @staticmethod
    def _move_subtask_to_running(status: SubtaskStatus, subtask_id: UUID) -> None:
        try:
            ensure_transition_allowed(status, SubtaskStatus.DISPATCHED)
            ensure_transition_allowed(SubtaskStatus.DISPATCHED, SubtaskStatus.RUNNING)
        except ValueError as exc:
            raise AppError(
                code="SUBTASK_STATE_CONFLICT",
                message=str(exc),
                status_code=409,
                details={
                    "subtask_id": str(subtask_id),
                    "current_status": status,
                    "target_status": SubtaskStatus.RUNNING,
                },
            ) from exc
