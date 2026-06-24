from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.enums import AlertSeverity, WorkerAlertType
from app.schemas.worker_alert import WorkerAlertListResponse
from app.services.worker_alert_service import WorkerAlertService

router = APIRouter(prefix="/worker-alerts")


@router.get("", response_model=WorkerAlertListResponse)
def list_worker_alerts(
    alert_type: WorkerAlertType | None = Query(default=None),
    severity: AlertSeverity | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> WorkerAlertListResponse:
    items, total = WorkerAlertService(db).list_alerts(
        alert_type=alert_type,
        severity=severity,
        page=page,
        page_size=page_size,
    )
    return WorkerAlertListResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
    )
