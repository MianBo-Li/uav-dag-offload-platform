from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Integer, JSON, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.enums import AlertSeverity, WorkerAlertType, WorkerStatus


class WorkerHeartbeat(Base):
    __tablename__ = "worker_heartbeats"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    worker_name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    hostname: Mapped[str] = mapped_column(String(128), nullable=False)
    process_id: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[WorkerStatus] = mapped_column(String(16), nullable=False)
    current_execution_id: Mapped[UUID | None] = mapped_column(Uuid)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class WorkerAlert(Base):
    __tablename__ = "worker_alerts"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    alert_type: Mapped[WorkerAlertType] = mapped_column(String(64), nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(String(16), nullable=False)
    worker_name: Mapped[str | None] = mapped_column(String(128))
    execution_id: Mapped[UUID | None] = mapped_column(Uuid, index=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details_json: Mapped[dict[str, object]] = mapped_column(
        "details",
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
