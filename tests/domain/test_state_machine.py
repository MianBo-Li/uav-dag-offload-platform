import pytest

from app.domain.enums import SubtaskStatus, TaskStatus
from app.domain.state_machine import can_transition, ensure_transition_allowed


def test_can_transition_allows_valid_task_transition() -> None:
    assert can_transition(TaskStatus.PENDING, TaskStatus.SCHEDULED)


def test_ensure_transition_allowed_rejects_invalid_task_transition() -> None:
    with pytest.raises(ValueError, match="Illegal state transition"):
        ensure_transition_allowed(TaskStatus.SUCCESS, TaskStatus.RUNNING)


def test_canceled_task_cannot_be_scheduled_or_run() -> None:
    assert not can_transition(TaskStatus.CANCELED, TaskStatus.SCHEDULED)
    assert not can_transition(TaskStatus.CANCELED, TaskStatus.RUNNING)


def test_running_subtask_can_be_canceled() -> None:
    assert can_transition(SubtaskStatus.RUNNING, SubtaskStatus.CANCELED)
