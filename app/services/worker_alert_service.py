from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.worker import WorkerAlert
from app.domain.enums import AlertSeverity, WorkerAlertType
from app.repositories.worker_alert_repository import WorkerAlertRepository


@dataclass(frozen=True)
class WorkerAlertSnapshot:
    alerts_by_type: dict[str, int]


class WorkerAlertService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = WorkerAlertRepository(db)

    def report_retry_exhausted(
        self,
        *,
        execution_id: UUID,
        worker_name: str,
        celery_task_id: str | None,
        retry_count: int,
        max_retries: int,
        exc: Exception,
    ) -> None:
        self.repository.create(
            alert_type=WorkerAlertType.CELERY_RETRY_EXHAUSTED,
            severity=AlertSeverity.ERROR,
            worker_name=worker_name,
            execution_id=execution_id,
            celery_task_id=celery_task_id,
            message="Celery execution retry budget exhausted",
            details={
                "retry_count": retry_count,
                "max_retries": max_retries,
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
            },
        )

    def load_snapshot(self) -> WorkerAlertSnapshot:
        return WorkerAlertSnapshot(alerts_by_type=self.repository.count_by_type())

    def list_alerts(
        self,
        *,
        alert_type: WorkerAlertType | None,
        severity: AlertSeverity | None,
        page: int,
        page_size: int,
    ) -> tuple[list[WorkerAlert], int]:
        return self.repository.list_alerts(
            alert_type=alert_type,
            severity=severity,
            page=page,
            page_size=page_size,
        )
