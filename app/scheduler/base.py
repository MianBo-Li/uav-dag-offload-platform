from typing import Protocol


class SchedulerStrategy(Protocol):
    name: str

    def generate_plan(
        self,
        task_graph: object,
        node_snapshot: object,
        options: dict[str, object] | None = None,
    ) -> object:
        ...
