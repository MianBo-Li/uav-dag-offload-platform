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
from app.repositories.execution_repository import ExecutionRepository
from app.services.execution_service import ExecutionService
from app.services.worker_alert_service import WorkerAlertService
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


def has_worker_retry_budget(retry_count: int, max_retries: int) -> bool:
    return retry_count < max_retries


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


def report_retry_exhausted_alert(
    *,
    execution_id: UUID,
    worker_name: str,
    celery_task_id: str | None,
    retry_count: int,
    max_retries: int,
    exc: Exception,
) -> None:
    db = SessionLocal()
    try:
        WorkerAlertService(db).report_retry_exhausted(
            execution_id=execution_id,
            worker_name=worker_name,
            celery_task_id=celery_task_id,
            retry_count=retry_count,
            max_retries=max_retries,
            exc=exc,
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.warning("Failed to report retry exhausted alert", exc_info=True)
    finally:
        db.close()


def is_execution_canceled(execution_id: UUID) -> bool:
    db = SessionLocal()
    try:
        record = ExecutionRepository(db).get_plain_by_id(execution_id)
        return record is not None and record.status == ExecutionStatus.CANCELED
    finally:
        db.close()


def sleep_with_cancel_checks(
    execution_id: UUID,
    total_seconds: float,
    check_interval_seconds: float,
    *,
    sleep_fn=sleep,
    cancel_check_fn=is_execution_canceled,
) -> bool:
    if total_seconds <= 0:
        return cancel_check_fn(execution_id)

    interval_seconds = (
        total_seconds if check_interval_seconds <= 0 else check_interval_seconds
    )
    remaining_seconds = total_seconds
    while remaining_seconds > 0:
        if cancel_check_fn(execution_id):
            return True

        current_sleep_seconds = min(interval_seconds, remaining_seconds)
        sleep_fn(current_sleep_seconds)
        remaining_seconds -= current_sleep_seconds

    return cancel_check_fn(execution_id)


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
    db = None
    try:
        execution_canceled = sleep_with_cancel_checks(
            execution_uuid,
            settings.simulated_execution_sleep_seconds,
            settings.worker_cancel_check_interval_seconds,
        )
        final_status = (
            ExecutionStatus.CANCELED
            if execution_canceled
            else ExecutionStatus(result_status)
        )
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
        effective_failure_reason = (
            failure_reason
            if failure_reason is not None
            else (
                "execution canceled before worker completion"
                if execution_canceled
                else None
            )
        )

        db = SessionLocal()
        result = ExecutionService(db).report_result(
            execution_uuid,
            final_status,
            duration_ms=effective_duration_ms,
            output_summary=effective_output_summary,
            failure_reason=effective_failure_reason,
        )
        db.commit()
        return {
            "execution_id": str(result.execution_id),
            "subtask_status": result.subtask_status,
            "task_status": result.task_status,
            "accepted": result.accepted,
        }
    except Exception as exc:
        if db is not None:
            db.rollback()
        if is_retryable_worker_exception(exc):
            retry_count = self.request.retries
            max_retries = settings.celery_execution_max_retries
            if not has_worker_retry_budget(retry_count, max_retries):
                report_retry_exhausted_alert(
                    execution_id=execution_uuid,
                    worker_name=worker_name,
                    celery_task_id=getattr(self.request, "id", None),
                    retry_count=retry_count,
                    max_retries=max_retries,
                    exc=exc,
                )
                logger.error(
                    "Execution task %s exhausted retry budget after %s retries",
                    execution_id,
                    retry_count,
                    exc_info=True,
                )
                raise

            retry_countdown = calculate_retry_countdown(
                retry_count,
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
        if db is not None:
            db.close()
        report_worker_heartbeat(worker_name=worker_name, status=WorkerStatus.ONLINE)
