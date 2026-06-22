from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.worker import WorkerHeartbeat
from app.domain.enums import WorkerStatus


class WorkerRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_name(self, worker_name: str) -> WorkerHeartbeat | None:
        return self.db.scalar(
            select(WorkerHeartbeat).where(WorkerHeartbeat.worker_name == worker_name)
        )

    def upsert_heartbeat(
        self,
        *,
        worker_name: str,
        hostname: str,
        process_id: int | None,
        status: WorkerStatus,
        current_execution_id: UUID | None,
        last_seen_at: datetime,
    ) -> WorkerHeartbeat:
        heartbeat = self.get_by_name(worker_name)
        if heartbeat is None:
            heartbeat = WorkerHeartbeat(
                worker_name=worker_name,
                hostname=hostname,
                process_id=process_id,
                status=status,
                current_execution_id=current_execution_id,
                last_seen_at=last_seen_at,
            )
            self.db.add(heartbeat)
        else:
            heartbeat.hostname = hostname
            heartbeat.process_id = process_id
            heartbeat.status = status
            heartbeat.current_execution_id = current_execution_id
            heartbeat.last_seen_at = last_seen_at

        self.db.flush()
        self.db.refresh(heartbeat)
        return heartbeat

    def count_total(self) -> int:
        return self.db.scalar(select(func.count()).select_from(WorkerHeartbeat)) or 0

    def count_seen_since(self, cutoff: datetime) -> int:
        return (
            self.db.scalar(
                select(func.count())
                .select_from(WorkerHeartbeat)
                .where(WorkerHeartbeat.last_seen_at >= cutoff)
            )
            or 0
        )

    def latest_seen_at(self) -> datetime | None:
        return self.db.scalar(select(func.max(WorkerHeartbeat.last_seen_at)))

    def count_by_status(self) -> dict[str, int]:
        rows = self.db.execute(
            select(WorkerHeartbeat.status, func.count()).group_by(WorkerHeartbeat.status)
        )
        return {str(key): count for key, count in rows}
