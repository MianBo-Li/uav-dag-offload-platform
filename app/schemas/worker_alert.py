from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import AlertSeverity, WorkerAlertType


class WorkerAlertRead(BaseModel):
    id: UUID
    alert_type: WorkerAlertType
    severity: AlertSeverity
    worker_name: str | None
    execution_id: UUID | None
    celery_task_id: str | None
    message: str
    details: dict[str, object] = Field(validation_alias="details_json")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkerAlertListResponse(BaseModel):
    items: list[WorkerAlertRead]
    page: int
    page_size: int
    total: int
