from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models.task import SchedulePlan


class ScheduleRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, plan: SchedulePlan) -> SchedulePlan:
        self.db.add(plan)
        self.db.flush()
        self.db.refresh(plan)
        return self.get_by_id(plan.id) or plan

    def get_by_id(self, plan_id: UUID) -> SchedulePlan | None:
        return self.db.scalar(
            select(SchedulePlan)
            .options(selectinload(SchedulePlan.items))
            .where(SchedulePlan.id == plan_id)
        )

    def list_by_task(
        self,
        task_id: UUID,
        page: int,
        page_size: int,
    ) -> tuple[list[SchedulePlan], int]:
        statement: Select[tuple[SchedulePlan]] = select(SchedulePlan).where(
            SchedulePlan.task_id == task_id
        )
        count_statement = (
            select(func.count())
            .select_from(SchedulePlan)
            .where(SchedulePlan.task_id == task_id)
        )

        total = self.db.scalar(count_statement) or 0
        items = list(
            self.db.scalars(
                statement.order_by(SchedulePlan.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return items, total
