import sys
from types import ModuleType
from uuid import uuid4

from app.domain.enums import ExecutionStatus
from app.services.execution_dispatcher import ExecutionDispatcher


class FakeCeleryTask:
    def __init__(self) -> None:
        self.sent_calls: list[tuple[str, dict[str, object]]] = []
        self.next_index = 0

    def delay(self, execution_id: str, **kwargs: object):
        self.sent_calls.append((execution_id, kwargs))
        self.next_index += 1
        return type("FakeAsyncResult", (), {"id": f"celery-task-{self.next_index}"})()


def test_execution_dispatcher_returns_zero_when_auto_enqueue_disabled() -> None:
    execution_ids = [uuid4()]

    dispatch_results = ExecutionDispatcher(
        auto_enqueue_enabled=False,
    ).enqueue_started_executions(execution_ids)

    assert dispatch_results == []


def test_execution_dispatcher_enqueues_each_started_execution(monkeypatch) -> None:
    fake_task = FakeCeleryTask()
    fake_worker_module = ModuleType("app.worker.tasks")
    fake_worker_module.execute_subtask = fake_task
    monkeypatch.setitem(sys.modules, "app.worker.tasks", fake_worker_module)
    execution_ids = [uuid4(), uuid4()]

    dispatch_results = ExecutionDispatcher(
        auto_enqueue_enabled=True,
    ).enqueue_started_executions(
        execution_ids,
        result_status=ExecutionStatus.FAILED,
        duration_ms=500,
        failure_reason="simulated failure",
    )

    assert len(dispatch_results) == 2
    assert [item.execution_id for item in dispatch_results] == execution_ids
    assert [item.celery_task_id for item in dispatch_results] == [
        "celery-task-1",
        "celery-task-2",
    ]
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
