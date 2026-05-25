from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models.task import DagTask
from app.domain.enums import TaskStatus


class TaskRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, task: DagTask) -> DagTask:
        self.db.add(task)
        self.db.flush()
        self.db.refresh(task)
        return task

    def get_by_id(self, task_id: UUID) -> DagTask | None:
        return self.db.scalar(
            select(DagTask)
            .options(selectinload(DagTask.subtasks), selectinload(DagTask.dependencies))
            .where(DagTask.id == task_id)
        )

    def list_tasks(
        self,
        status: TaskStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[list[DagTask], int]:
        statement: Select[tuple[DagTask]] = select(DagTask)
        count_statement = select(func.count()).select_from(DagTask)

        if status is not None:
            statement = statement.where(DagTask.status == status)
            count_statement = count_statement.where(DagTask.status == status)

        total = self.db.scalar(count_statement) or 0
        items = list(
            self.db.scalars(
                statement.order_by(DagTask.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return items, total
