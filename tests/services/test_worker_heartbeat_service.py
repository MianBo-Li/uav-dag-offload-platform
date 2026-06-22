from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.enums import WorkerStatus
from app.services.worker_heartbeat_service import WorkerHeartbeatService


def test_worker_heartbeat_upserts_by_worker_name(db_session: Session) -> None:
    service = WorkerHeartbeatService(db_session)
    reported_at = datetime(2026, 6, 22, 10, 0, tzinfo=UTC)

    first = service.report_heartbeat(
        worker_name="worker-a",
        hostname="host-a",
        process_id=1001,
        status=WorkerStatus.BUSY,
        reported_at=reported_at,
    )
    second = service.report_heartbeat(
        worker_name="worker-a",
        hostname="host-a",
        process_id=1001,
        status=WorkerStatus.ONLINE,
        reported_at=reported_at + timedelta(seconds=5),
    )

    assert second.id == first.id
    assert second.status == WorkerStatus.ONLINE
    assert second.current_execution_id is None
    assert service.load_snapshot().total_workers == 1


def test_worker_heartbeat_snapshot_counts_online_workers(db_session: Session) -> None:
    settings = Settings(worker_heartbeat_timeout_seconds=60)
    service = WorkerHeartbeatService(db_session, settings=settings)
    now = datetime(2026, 6, 22, 10, 1, tzinfo=UTC)
    service.report_heartbeat(
        worker_name="worker-online",
        hostname="host-a",
        process_id=1001,
        status=WorkerStatus.ONLINE,
        reported_at=now - timedelta(seconds=30),
    )
    service.report_heartbeat(
        worker_name="worker-stale",
        hostname="host-b",
        process_id=1002,
        status=WorkerStatus.BUSY,
        reported_at=now - timedelta(seconds=90),
    )

    snapshot = service.load_snapshot(now=now)

    assert snapshot.total_workers == 2
    assert snapshot.online_workers == 1
    assert snapshot.workers_by_status == {
        "BUSY": 1,
        "ONLINE": 1,
    }
    assert snapshot.latest_seen_timestamp == int(
        (now - timedelta(seconds=30)).timestamp()
    )
