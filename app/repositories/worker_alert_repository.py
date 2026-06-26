from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.worker import WorkerAlert
from app.domain.enums import AlertSeverity, WorkerAlertType


class WorkerAlertRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        alert_type: WorkerAlertType,
        severity: AlertSeverity,
        message: str,
        worker_name: str | None = None,
        execution_id: UUID | None = None,
        celery_task_id: str | None = None,
        details: dict[str, object] | None = None,
    ) -> WorkerAlert:
        alert = WorkerAlert(
            alert_type=alert_type,
            severity=severity,
            worker_name=worker_name,
            execution_id=execution_id,
            celery_task_id=celery_task_id,
            message=message,
            details_json=details or {},
        )
        self.db.add(alert)
        self.db.flush()
        return alert

    def count_by_type(self) -> dict[str, int]:
        rows = self.db.execute(
            select(WorkerAlert.alert_type, func.count()).group_by(
                WorkerAlert.alert_type
            )
        )
        return {str(alert_type): count for alert_type, count in rows}

    def list_alerts(
        self,
        *,
        alert_type: WorkerAlertType | None,
        severity: AlertSeverity | None,
        page: int,
        page_size: int,
    ) -> tuple[list[WorkerAlert], int]:
        statement = select(WorkerAlert)
        count_statement = select(func.count()).select_from(WorkerAlert)

        if alert_type is not None:
            statement = statement.where(WorkerAlert.alert_type == alert_type)
            count_statement = count_statement.where(WorkerAlert.alert_type == alert_type)
        if severity is not None:
            statement = statement.where(WorkerAlert.severity == severity)
            count_statement = count_statement.where(WorkerAlert.severity == severity)

        total = self.db.scalar(count_statement) or 0
        items = list(
            self.db.scalars(
                statement.order_by(WorkerAlert.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return items, total
