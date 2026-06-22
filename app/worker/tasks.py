import os
import socket
from time import sleep
from uuid import UUID

from celery import Task
from celery.utils.log import get_task_logger
from sqlalchemy.exc import DBAPIError, OperationalError, TimeoutError as SQLAlchemyTimeoutError

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.session import SessionLocal
from app.domain.enums import ExecutionStatus, WorkerStatus
from app.services.execution_service import ExecutionService
from app.services.worker_heartbeat_service import WorkerHeartbeatService
from app.worker.celery_app import celery_app

logger = get_task_logger(__name__)


def is_retryable_worker_exception(exc: Exception) -> bool:
    if isinstance(exc, AppError):
        return False
    if isinstance(exc, OperationalError | SQLAlchemyTimeoutError):
        return True
    if isinstance(exc, DBAPIError):
        return exc.connection_invalidated
    return False


def calculate_retry_countdown(
    retry_count: int,
    base_seconds: int,
    max_seconds: int,
) -> int:
    return min(base_seconds * (2**retry_count), max_seconds)


def resolve_worker_name(task: Task) -> str:
    hostname = getattr(task.request, "hostname", None)
    return str(hostname or socket.gethostname())


def report_worker_heartbeat(
    *,
    worker_name: str,
    status: WorkerStatus,
    current_execution_id: UUID | None = None,
) -> None:
    db = SessionLocal()
    try:
        WorkerHeartbeatService(db).report_heartbeat(
            worker_name=worker_name,
            hostname=socket.gethostname(),
            process_id=os.getpid(),
            status=status,
            current_execution_id=current_execution_id,
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.warning("Failed to report worker heartbeat", exc_info=True)
    finally:
        db.close()


@celery_app.task(name="app.worker.tasks.execute_subtask", bind=True)
def execute_subtask(
    self: Task,
    execution_id: str,
    result_status: str = ExecutionStatus.SUCCESS.value,
    duration_ms: int | None = None,
    output_summary: str | None = None,
    failure_reason: str | None = None,
) -> dict[str, object]:
    settings = get_settings()
    execution_uuid = UUID(execution_id)
    worker_name = resolve_worker_name(self)
    report_worker_heartbeat(
        worker_name=worker_name,
        status=WorkerStatus.BUSY,
        current_execution_id=execution_uuid,
    )
    if settings.simulated_execution_sleep_seconds > 0:
        sleep(settings.simulated_execution_sleep_seconds)

    final_status = ExecutionStatus(result_status)
    effective_duration_ms = (
        settings.simulated_execution_duration_ms
        if duration_ms is None
        else duration_ms
    )
    effective_output_summary = (
        output_summary
        if output_summary is not None
        else "simulated execution completed by celery worker"
    )

    db = SessionLocal()
    try:
        result = ExecutionService(db).report_result(
            execution_uuid,
            final_status,
            duration_ms=effective_duration_ms,
            output_summary=effective_output_summary,
            failure_reason=failure_reason,
        )
        db.commit()
        return {
            "execution_id": str(result.execution_id),
            "subtask_status": result.subtask_status,
            "task_status": result.task_status,
            "accepted": result.accepted,
        }
    except Exception as exc:
        db.rollback()
        if is_retryable_worker_exception(exc):
            retry_countdown = calculate_retry_countdown(
                self.request.retries,
                settings.celery_execution_retry_backoff_seconds,
                settings.celery_execution_retry_backoff_max_seconds,
            )
            logger.warning(
                "Retrying execution task %s after retryable worker error in %s seconds",
                execution_id,
                retry_countdown,
                exc_info=True,
            )
            raise self.retry(
                exc=exc,
                countdown=retry_countdown,
                max_retries=settings.celery_execution_max_retries,
            ) from exc

        logger.exception("Failed to execute subtask %s", execution_id)
        raise
    finally:
        db.close()
        report_worker_heartbeat(worker_name=worker_name, status=WorkerStatus.ONLINE)
