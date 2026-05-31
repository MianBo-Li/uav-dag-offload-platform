from collections.abc import Iterable
from uuid import UUID

from app.core.config import get_settings
from app.domain.enums import ExecutionStatus


class ExecutionDispatcher:
    def __init__(self, auto_enqueue_enabled: bool | None = None) -> None:
        settings = get_settings()
        self.auto_enqueue_enabled = (
            settings.execution_auto_enqueue_enabled
            if auto_enqueue_enabled is None
            else auto_enqueue_enabled
        )

    def enqueue_started_executions(
        self,
        execution_ids: Iterable[UUID],
        result_status: ExecutionStatus = ExecutionStatus.SUCCESS,
        duration_ms: int | None = None,
        output_summary: str | None = None,
        failure_reason: str | None = None,
    ) -> int:
        execution_id_list = list(execution_ids)
        if not self.auto_enqueue_enabled:
            return 0

        from app.worker.tasks import execute_subtask

        for execution_id in execution_id_list:
            execute_subtask.delay(
                str(execution_id),
                result_status=result_status,
                duration_ms=duration_ms,
                output_summary=output_summary,
                failure_reason=failure_reason,
            )
        return len(execution_id_list)
