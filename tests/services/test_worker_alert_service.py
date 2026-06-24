from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.models.worker import WorkerAlert
from app.domain.enums import AlertSeverity, WorkerAlertType
from app.services.worker_alert_service import WorkerAlertService


def test_report_retry_exhausted_creates_worker_alert(db_session: Session) -> None:
    execution_id = uuid4()

    WorkerAlertService(db_session).report_retry_exhausted(
        execution_id=execution_id,
        worker_name="worker-a",
        celery_task_id="celery-task-123",
        retry_count=3,
        max_retries=3,
        exc=RuntimeError("database unavailable"),
    )

    alert = db_session.query(WorkerAlert).one()
    assert alert.alert_type == WorkerAlertType.CELERY_RETRY_EXHAUSTED
    assert alert.severity == AlertSeverity.ERROR
    assert alert.worker_name == "worker-a"
    assert alert.execution_id == execution_id
    assert alert.celery_task_id == "celery-task-123"
    assert alert.message == "Celery execution retry budget exhausted"
    assert alert.details_json == {
        "retry_count": 3,
        "max_retries": 3,
        "exception_type": "RuntimeError",
        "exception_message": "database unavailable",
    }


def test_worker_alert_snapshot_counts_alerts_by_type(db_session: Session) -> None:
    service = WorkerAlertService(db_session)
    service.report_retry_exhausted(
        execution_id=uuid4(),
        worker_name="worker-a",
        celery_task_id=None,
        retry_count=3,
        max_retries=3,
        exc=RuntimeError("database unavailable"),
    )

    snapshot = service.load_snapshot()

    assert snapshot.alerts_by_type == {
        "CELERY_RETRY_EXHAUSTED": 1,
    }
