from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.models.task import DagTask
from app.db.session import get_db
from app.domain.enums import TaskStatus
from app.schemas.task import (
    DagDependencyRead,
    DagTaskCreate,
    DagTaskDetailRead,
    DagTaskListResponse,
    DagTaskRead,
)
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
