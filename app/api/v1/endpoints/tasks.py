from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.models.task import DagTask, SchedulePlan
from app.db.session import get_db
from app.domain.enums import ExecutionStatus, SubtaskStatus, TaskStatus
from app.schemas.execution import (
    ExecutionRecordListResponse,
    ExecutionStartRequest,
    ExecutionStartResponse,
)
from app.schemas.metrics import TaskMetricsRead
from app.schemas.schedule import (
    ScheduleComparisonResponse,
    SchedulePlanListResponse,
    SchedulePlanRead,
    ScheduleRequest,
)
from app.schemas.task import (
    DagDependencyRead,
    DagSubtaskListResponse,
    DagTaskCancelRequest,
    DagTaskCancelResponse,
    DagTaskCreate,
    DagTaskDetailRead,
    DagTaskListResponse,
    DagTaskRead,
)
from app.services.execution_dispatcher import ExecutionDispatcher
from app.services.execution_service import (
    ExecutionDispatchRegistration,
    ExecutionService,
)
from app.services.metrics_service import MetricsService
from app.services.scheduling_service import SchedulingService
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks")


def _ensure_utc(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=UTC)


def _task_to_read(task: DagTask) -> DagTaskRead:
    return DagTaskRead(
        id=task.id,
        name=task.name,
        status=task.status,
        priority=task.priority,
        deadline_at=_ensure_utc(task.deadline_at),
        subtask_count=len(task.subtasks),
        dependency_count=len(task.dependencies),
        created_at=_ensure_utc(task.created_at),
    )


def _task_to_detail(task: DagTask) -> DagTaskDetailRead:
    subtask_external_ids = {
        subtask.id: subtask.external_id for subtask in task.subtasks
    }
    return DagTaskDetailRead(
        id=task.id,
        name=task.name,
        status=task.status,
        priority=task.priority,
        deadline_at=_ensure_utc(task.deadline_at),
        subtasks=task.subtasks,
        dependencies=[
            DagDependencyRead(
                from_=subtask_external_ids[dependency.predecessor_subtask_id],
                to=subtask_external_ids[dependency.successor_subtask_id],
            )
            for dependency in task.dependencies
        ],
        created_at=_ensure_utc(task.created_at),
        updated_at=_ensure_utc(task.updated_at),
    )


def _schedule_plan_to_read(plan: SchedulePlan) -> SchedulePlanRead:
    return SchedulePlanRead(
        id=plan.id,
        task_id=plan.task_id,
        strategy_name=plan.strategy_name,
        status=plan.status,
        estimated_total_duration_ms=plan.estimated_total_duration_ms,
        estimated_total_energy=(
            float(plan.estimated_total_energy)
            if plan.estimated_total_energy is not None
            else None
        ),
        items=plan.items,
        created_at=_ensure_utc(plan.created_at),
    )


@router.post("", response_model=DagTaskRead, status_code=status.HTTP_201_CREATED)
def create_task(payload: DagTaskCreate, db: Session = Depends(get_db)) -> DagTaskRead:
    task = TaskService(db).create_task(payload)
    db.commit()
    task = TaskService(db).get_task(task.id)
    return _task_to_read(task)


@router.get("", response_model=DagTaskListResponse)
def list_tasks(
    status_filter: TaskStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> DagTaskListResponse:
    items, total = TaskService(db).list_tasks(status_filter, page, page_size)
    return DagTaskListResponse(items=items, page=page, page_size=page_size, total=total)


@router.get("/{task_id}", response_model=DagTaskDetailRead)
def get_task(task_id: UUID, db: Session = Depends(get_db)) -> DagTaskDetailRead:
    task = TaskService(db).get_task(task_id)
    return _task_to_detail(task)


@router.get("/{task_id}/subtasks", response_model=DagSubtaskListResponse)
def list_task_subtasks(
    task_id: UUID,
    status_filter: SubtaskStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> DagSubtaskListResponse:
    items, total = TaskService(db).list_subtasks(
        task_id,
        status_filter,
        page,
        page_size,
    )
    return DagSubtaskListResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post(
    "/{task_id}/schedule",
    response_model=SchedulePlanRead,
    status_code=status.HTTP_201_CREATED,
)
def schedule_task(
    task_id: UUID,
    payload: ScheduleRequest = Body(default_factory=ScheduleRequest),
    db: Session = Depends(get_db),
) -> SchedulePlanRead:
    plan = SchedulingService(db).generate_plan(
        task_id,
        payload.strategy_name,
        payload.options,
    )
    db.commit()
    return _schedule_plan_to_read(plan)


@router.get("/{task_id}/schedules", response_model=SchedulePlanListResponse)
def list_task_schedules(
    task_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> SchedulePlanListResponse:
    items, total = SchedulingService(db).list_task_plans(task_id, page, page_size)
    return SchedulePlanListResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{task_id}/schedule-comparison", response_model=ScheduleComparisonResponse)
def compare_task_schedules(
    task_id: UUID,
    db: Session = Depends(get_db),
) -> ScheduleComparisonResponse:
    items = SchedulingService(db).compare_strategies(task_id)
    return ScheduleComparisonResponse(task_id=task_id, items=items)


@router.post(
    "/{task_id}/execute",
    response_model=ExecutionStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def execute_task(
    task_id: UUID,
    payload: ExecutionStartRequest,
    db: Session = Depends(get_db),
) -> ExecutionStartResponse:
    execution_service = ExecutionService(db)
    result = execution_service.start_execution(task_id, payload.schedule_plan_id)
    db.commit()
    simulation = payload.simulation
    dispatch_results = ExecutionDispatcher().enqueue_started_executions(
        result.execution_ids,
        result_status=(
            simulation.result_status if simulation is not None else ExecutionStatus.SUCCESS
        ),
        duration_ms=simulation.duration_ms if simulation is not None else None,
        output_summary=simulation.output_summary if simulation is not None else None,
        failure_reason=simulation.failure_reason if simulation is not None else None,
    )
    execution_service.record_celery_task_ids(
        [
            ExecutionDispatchRegistration(
                execution_id=item.execution_id,
                celery_task_id=item.celery_task_id,
            )
            for item in dispatch_results
        ]
    )
    db.commit()
    return ExecutionStartResponse(
        task_id=result.task_id,
        schedule_plan_id=result.schedule_plan_id,
        status=result.status,
        execution_count=result.execution_count,
        execution_ids=result.execution_ids,
        queued_count=len(dispatch_results),
    )


@router.get("/{task_id}/executions", response_model=ExecutionRecordListResponse)
def list_task_executions(
    task_id: UUID,
    status_filter: ExecutionStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ExecutionRecordListResponse:
    items, total = ExecutionService(db).list_task_executions(
        task_id,
        status_filter,
        page,
        page_size,
    )
    return ExecutionRecordListResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{task_id}/metrics", response_model=TaskMetricsRead)
def get_task_metrics(
    task_id: UUID,
    db: Session = Depends(get_db),
) -> TaskMetricsRead:
    return MetricsService(db).get_task_metrics(task_id)


@router.post("/{task_id}/cancel", response_model=DagTaskCancelResponse)
def cancel_task(
    task_id: UUID,
    payload: DagTaskCancelRequest,
    db: Session = Depends(get_db),
) -> DagTaskCancelResponse:
    task = TaskService(db).cancel_task(task_id, payload)
    db.commit()
    db.refresh(task)
    return DagTaskCancelResponse(
        task_id=task.id,
        status=task.status,
        reason=task.failure_reason,
        updated_at=_ensure_utc(task.updated_at),
    )
