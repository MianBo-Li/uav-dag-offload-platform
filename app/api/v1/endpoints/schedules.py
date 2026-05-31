from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.models.task import SchedulePlan
from app.db.session import get_db
from app.schemas.schedule import SchedulePlanRead
from app.services.scheduling_service import SchedulingService

router = APIRouter(prefix="/schedules")


def _ensure_utc(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=UTC)


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


@router.get("/{schedule_plan_id}", response_model=SchedulePlanRead)
def get_schedule_plan(
    schedule_plan_id: UUID,
    db: Session = Depends(get_db),
) -> SchedulePlanRead:
    plan = SchedulingService(db).get_plan(schedule_plan_id)
    return _schedule_plan_to_read(plan)
