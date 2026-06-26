from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.task import ExecutionRevokeEvent
from app.db.models.node import Node, NodeStatusRecord
from app.domain.enums import (
    ExecutionStatus,
    NodeType,
    SchedulerStrategyName,
    SubtaskExecutionConstraint,
)
from app.repositories.execution_repository import ExecutionRepository
from app.schemas.task import DagTaskCancelRequest, DagTaskCreate, SubtaskCreate
from app.services.execution_service import (
    ExecutionDispatchRegistration,
    ExecutionService,
)
from app.services.scheduling_service import SchedulingService
from app.services.task_service import TaskService


def _task_payload() -> DagTaskCreate:
    return DagTaskCreate(
        name="inspection-task-001",
        priority=1,
        subtasks=[
            SubtaskCreate(
                external_id="capture_image",
                name="Capture image",
                compute_load=80.0,
                input_data_size_mb=0.0,
                output_data_size_mb=120.0,
                execution_constraint=SubtaskExecutionConstraint.LOCAL_ONLY,
            ),
        ],
    )


def _create_uav_node(db_session: Session) -> Node:
    node = Node(
        name="UAV-001",
        node_type=NodeType.UAV,
        cpu_capacity=100.0,
        memory_capacity_mb=2048,
    )
    db_session.add(node)
    db_session.flush()
    db_session.refresh(node)

    db_session.add(
        NodeStatusRecord(
            node_id=node.id,
            cpu_usage=0.0,
            memory_usage=30.0,
            reported_at=datetime(2026, 6, 8, 10, 0, tzinfo=UTC),
        )
    )
    db_session.flush()
    return node


def _start_ready_execution(db_session: Session) -> UUID:
    task = TaskService(db_session).create_task(_task_payload())
    _create_uav_node(db_session)
    plan = SchedulingService(db_session).generate_plan(
        task.id,
        SchedulerStrategyName.GREEDY,
    )
    result = ExecutionService(db_session).start_execution(task.id, plan.id)
    return result.execution_ids[0]


def test_report_result_uses_locked_execution_lookup(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    execution_id = _start_ready_execution(db_session)
    locked_lookup_ids: list[UUID] = []
    original_get_by_id_for_update = ExecutionRepository.get_by_id_for_update

    def tracking_get_by_id_for_update(
        self: ExecutionRepository,
        lookup_id: UUID,
    ):
        locked_lookup_ids.append(lookup_id)
        return original_get_by_id_for_update(self, lookup_id)

    monkeypatch.setattr(
        ExecutionRepository,
        "get_by_id_for_update",
        tracking_get_by_id_for_update,
    )

    result = ExecutionService(db_session).report_result(
        execution_id,
        ExecutionStatus.SUCCESS,
        duration_ms=250,
        output_summary="image captured",
    )

    assert locked_lookup_ids == [execution_id]
    assert result.accepted is True


def test_record_celery_task_ids_updates_execution_record(db_session: Session) -> None:
    execution_id = _start_ready_execution(db_session)

    ExecutionService(db_session).record_celery_task_ids(
        [
            ExecutionDispatchRegistration(
                execution_id=execution_id,
                celery_task_id="celery-task-123",
            )
        ]
    )

    record = ExecutionRepository(db_session).get_plain_by_id(execution_id)
    assert record is not None
    assert record.celery_task_id == "celery-task-123"


def test_cancel_running_execution_revokes_celery_task(db_session: Session) -> None:
    execution_id = _start_ready_execution(db_session)
    record = ExecutionRepository(db_session).get_plain_by_id(execution_id)
    assert record is not None
    record.celery_task_id = "celery-task-123"

    class FakeExecutionRevoker:
        def __init__(self) -> None:
            self.revoked_ids: list[str] = []

        def revoke(self, celery_task_id: str) -> bool:
            self.revoked_ids.append(celery_task_id)
            return True

    revoker = FakeExecutionRevoker()
    TaskService(db_session, execution_revoker=revoker).cancel_task(
        record.task_id,
        DagTaskCancelRequest(reason="operator canceled during execution"),
    )

    assert revoker.revoked_ids == ["celery-task-123"]

    events = list(db_session.scalars(select(ExecutionRevokeEvent)))
    assert len(events) == 1
    assert events[0].task_id == record.task_id
    assert events[0].execution_id == record.id
    assert events[0].celery_task_id == "celery-task-123"
    assert events[0].success is True
    assert events[0].error_message is None


def test_cancel_running_execution_records_failed_revoke_event(
    db_session: Session,
) -> None:
    execution_id = _start_ready_execution(db_session)
    record = ExecutionRepository(db_session).get_plain_by_id(execution_id)
    assert record is not None
    record.celery_task_id = "celery-task-123"

    class FakeExecutionRevoker:
        def revoke(self, celery_task_id: str) -> bool:
            assert celery_task_id == "celery-task-123"
            return False

    TaskService(db_session, execution_revoker=FakeExecutionRevoker()).cancel_task(
        record.task_id,
        DagTaskCancelRequest(reason="operator canceled during execution"),
    )

    events = list(db_session.scalars(select(ExecutionRevokeEvent)))
    assert len(events) == 1
    assert events[0].success is False
    assert events[0].error_message == "Celery revoke returned false"
