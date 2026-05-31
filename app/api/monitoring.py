from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.monitoring_repository import MonitoringRepository
from app.services.monitoring_service import MonitoringService

router = APIRouter()


@router.get("/metrics", include_in_schema=False)
def prometheus_metrics(db: Session = Depends(get_db)) -> Response:
    content = MonitoringService(MonitoringRepository(db)).render_prometheus_metrics()
    return Response(content=content, media_type="text/plain; version=0.0.4")
