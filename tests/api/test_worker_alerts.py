from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.worker_alert_service import WorkerAlertService


def test_list_worker_alerts_returns_retry_exhausted_alert(
    client: TestClient,
    db_session: Session,
) -> None:
    WorkerAlertService(db_session).report_retry_exhausted(
        execution_id=UUID("00000000-0000-0000-0000-000000000001"),
        worker_name="worker-a",
        celery_task_id="celery-task-123",
        retry_count=3,
        max_retries=3,
        exc=RuntimeError("database unavailable"),
    )
    db_session.commit()

    response = client.get("/api/v1/worker-alerts")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["page"] == 1
    assert body["page_size"] == 20

    item = body["items"][0]
    assert item["alert_type"] == "CELERY_RETRY_EXHAUSTED"
    assert item["severity"] == "ERROR"
    assert item["worker_name"] == "worker-a"
    assert item["execution_id"] == "00000000-0000-0000-0000-000000000001"
    assert item["celery_task_id"] == "celery-task-123"
    assert item["message"] == "Celery execution retry budget exhausted"
    assert item["details"]["retry_count"] == 3
    assert item["details"]["exception_type"] == "RuntimeError"


def test_list_worker_alerts_filters_by_type_and_severity(
    client: TestClient,
    db_session: Session,
) -> None:
    WorkerAlertService(db_session).report_retry_exhausted(
        execution_id=UUID("00000000-0000-0000-0000-000000000001"),
        worker_name="worker-a",
        celery_task_id=None,
        retry_count=3,
        max_retries=3,
        exc=RuntimeError("database unavailable"),
    )
    db_session.commit()

    response = client.get(
        "/api/v1/worker-alerts",
        params={
            "alert_type": "CELERY_RETRY_EXHAUSTED",
            "severity": "ERROR",
        },
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1

    empty_response = client.get(
        "/api/v1/worker-alerts",
        params={"severity": "WARNING"},
    )

    assert empty_response.status_code == 200
    assert empty_response.json()["total"] == 0
