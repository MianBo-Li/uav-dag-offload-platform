from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.execution import ExecutionResultRequest, ExecutionResultResponse
from app.services.execution_service import ExecutionService

router = APIRouter(prefix="/executions")


@router.post("/{execution_id}/result", response_model=ExecutionResultResponse)
def report_execution_result(
    execution_id: UUID,
    payload: ExecutionResultRequest,
    db: Session = Depends(get_db),
) -> ExecutionResultResponse:
    result = ExecutionService(db).report_result(
        execution_id,
        payload.status,
        payload.duration_ms,
        payload.output_summary,
        payload.failure_reason,
    )
    db.commit()
    return ExecutionResultResponse(
        execution_id=result.execution_id,
        subtask_status=result.subtask_status,
        task_status=result.task_status,
        accepted=result.accepted,
    )
