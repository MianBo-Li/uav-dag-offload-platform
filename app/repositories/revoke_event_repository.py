from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.task import ExecutionRevokeEvent


class RevokeEventRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        task_id: UUID,
        execution_id: UUID,
        celery_task_id: str,
        success: bool,
        error_message: str | None,
        requested_at: datetime,
    ) -> ExecutionRevokeEvent:
        event = ExecutionRevokeEvent(
            task_id=task_id,
            execution_id=execution_id,
            celery_task_id=celery_task_id,
            success=success,
            error_message=error_message,
            requested_at=requested_at,
        )
        self.db.add(event)
        self.db.flush()
        return event
