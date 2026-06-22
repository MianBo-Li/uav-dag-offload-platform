from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.models.worker import WorkerHeartbeat
from app.domain.enums import WorkerStatus
from app.repositories.worker_repository import WorkerRepository


@dataclass(frozen=True)
class WorkerHeartbeatSnapshot:
    total_workers: int
    online_workers: int
    latest_seen_at: datetime | str | None
    workers_by_status: dict[str, int]

    @property
    def latest_seen_timestamp(self) -> int:
        if self.latest_seen_at is None:
            return 0
        latest_seen_at = self.latest_seen_at
        if isinstance(latest_seen_at, str):
            latest_seen_at = datetime.fromisoformat(latest_seen_at)
        if latest_seen_at.tzinfo is None:
            latest_seen_at = latest_seen_at.replace(tzinfo=UTC)
        return int(latest_seen_at.timestamp())


class WorkerHeartbeatService:
    def __init__(
        self,
        db: Session,
        settings: Settings | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.repository = WorkerRepository(db)

    def report_heartbeat(
        self,
        *,
        worker_name: str,
        hostname: str,
        process_id: int | None,
        status: WorkerStatus,
        current_execution_id: UUID | None = None,
        reported_at: datetime | None = None,
    ) -> WorkerHeartbeat:
        seen_at = reported_at or datetime.now(UTC)
        return self.repository.upsert_heartbeat(
            worker_name=worker_name,
            hostname=hostname,
            process_id=process_id,
            status=status,
            current_execution_id=current_execution_id,
            last_seen_at=seen_at,
        )

    def load_snapshot(self, now: datetime | None = None) -> WorkerHeartbeatSnapshot:
        reference_time = now or datetime.now(UTC)
        cutoff = reference_time - timedelta(
            seconds=self.settings.worker_heartbeat_timeout_seconds
        )
        return WorkerHeartbeatSnapshot(
            total_workers=self.repository.count_total(),
            online_workers=self.repository.count_seen_since(cutoff),
            latest_seen_at=self.repository.latest_seen_at(),
            workers_by_status=self.repository.count_by_status(),
        )
