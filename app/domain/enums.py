from enum import StrEnum


class NodeType(StrEnum):
    UAV = "UAV"
    EDGE = "EDGE"


class NodeStatus(StrEnum):
    ONLINE = "ONLINE"
    BUSY = "BUSY"
    OFFLINE = "OFFLINE"


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    SCHEDULED = "SCHEDULED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class SubtaskStatus(StrEnum):
    WAITING = "WAITING"
    READY = "READY"
    DISPATCHED = "DISPATCHED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RETRYING = "RETRYING"


class SubtaskExecutionConstraint(StrEnum):
    OFFLOADABLE = "OFFLOADABLE"
    LOCAL_ONLY = "LOCAL_ONLY"
    EDGE_ONLY = "EDGE_ONLY"


class SchedulePlanStatus(StrEnum):
    GENERATED = "GENERATED"
    APPLIED = "APPLIED"
    CANCELED = "CANCELED"


class ExecutionStatus(StrEnum):
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    CANCELED = "CANCELED"


class SchedulerStrategyName(StrEnum):
    LOCAL_ONLY = "local_only"
    RANDOM_OFFLOAD = "random_offload"
    GREEDY = "greedy"
