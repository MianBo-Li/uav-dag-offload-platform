from time import sleep
from uuid import UUID

from celery.utils.log import get_task_logger

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.domain.enums import ExecutionStatus
from app.services.execution_service import ExecutionService
from app.worker.celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(name="app.worker.tasks.execute_subtask")
def execute_subtask(
    execution_id: str,
    result_status: str = ExecutionStatus.SUCCESS.value,
    duration_ms: int | None = None,
    output_summary: str | None = None,
    failure_reason: str | None = None,
) -> dict[str, object]:
    settings = get_settings()
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
            UUID(execution_id),
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
    except Exception:
        db.rollback()
        logger.exception("Failed to execute subtask %s", execution_id)
        raise
    finally:
        db.close()
