from app.domain.enums import (
    ExecutionStatus,
    NodeStatus,
    SchedulePlanStatus,
    SubtaskStatus,
    TaskStatus,
)

State = TaskStatus | SubtaskStatus | NodeStatus | SchedulePlanStatus | ExecutionStatus

ALLOWED_TRANSITIONS: dict[State, set[State]] = {
    TaskStatus.PENDING: {TaskStatus.SCHEDULED, TaskStatus.CANCELED},
    TaskStatus.SCHEDULED: {TaskStatus.RUNNING, TaskStatus.CANCELED},
    TaskStatus.RUNNING: {TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.CANCELED},
    SubtaskStatus.WAITING: {SubtaskStatus.READY, SubtaskStatus.CANCELED},
    SubtaskStatus.READY: {SubtaskStatus.DISPATCHED, SubtaskStatus.CANCELED},
    SubtaskStatus.DISPATCHED: {SubtaskStatus.RUNNING, SubtaskStatus.CANCELED},
    SubtaskStatus.RUNNING: {
        SubtaskStatus.SUCCESS,
        SubtaskStatus.FAILED,
        SubtaskStatus.CANCELED,
    },
    SubtaskStatus.FAILED: {SubtaskStatus.RETRYING},
    SubtaskStatus.RETRYING: {SubtaskStatus.READY, SubtaskStatus.CANCELED},
    NodeStatus.ONLINE: {NodeStatus.BUSY, NodeStatus.OFFLINE},
    NodeStatus.BUSY: {NodeStatus.ONLINE, NodeStatus.OFFLINE},
    NodeStatus.OFFLINE: {NodeStatus.ONLINE},
    SchedulePlanStatus.GENERATED: {
        SchedulePlanStatus.APPLIED,
        SchedulePlanStatus.CANCELED,
    },
    SchedulePlanStatus.APPLIED: {SchedulePlanStatus.CANCELED},
    ExecutionStatus.RUNNING: {
        ExecutionStatus.SUCCESS,
        ExecutionStatus.FAILED,
        ExecutionStatus.TIMEOUT,
        ExecutionStatus.CANCELED,
    },
}


def can_transition(current_state: State, target_state: State) -> bool:
    return target_state in ALLOWED_TRANSITIONS.get(current_state, set())


def ensure_transition_allowed(current_state: State, target_state: State) -> None:
    if not can_transition(current_state, target_state):
        raise ValueError(f"Illegal state transition: {current_state} -> {target_state}")
