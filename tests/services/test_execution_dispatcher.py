import sys
from types import ModuleType
from uuid import uuid4

from app.domain.enums import ExecutionStatus
from app.services.execution_dispatcher import ExecutionDispatcher


class FakeCeleryTask:
    def __init__(self) -> None:
        self.sent_calls: list[tuple[str, dict[str, object]]] = []

    def delay(self, execution_id: str, **kwargs: object) -> None:
        self.sent_calls.append((execution_id, kwargs))


def test_execution_dispatcher_returns_zero_when_auto_enqueue_disabled() -> None:
    execution_ids = [uuid4()]

    queued_count = ExecutionDispatcher(
        auto_enqueue_enabled=False,
    ).enqueue_started_executions(execution_ids)

    assert queued_count == 0


def test_execution_dispatcher_enqueues_each_started_execution(monkeypatch) -> None:
    fake_task = FakeCeleryTask()
    fake_worker_module = ModuleType("app.worker.tasks")
    fake_worker_module.execute_subtask = fake_task
    monkeypatch.setitem(sys.modules, "app.worker.tasks", fake_worker_module)
    execution_ids = [uuid4(), uuid4()]

    queued_count = ExecutionDispatcher(
        auto_enqueue_enabled=True,
    ).enqueue_started_executions(
        execution_ids,
        result_status=ExecutionStatus.FAILED,
        duration_ms=500,
        failure_reason="simulated failure",
    )

    assert queued_count == 2
    assert [call[0] for call in fake_task.sent_calls] == [
        str(execution_id) for execution_id in execution_ids
    ]
    assert all(
        call[1]
        == {
            "result_status": ExecutionStatus.FAILED,
            "duration_ms": 500,
            "output_summary": None,
            "failure_reason": "simulated failure",
        }
        for call in fake_task.sent_calls
    )
