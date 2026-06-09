from app.repositories.monitoring_repository import MonitoringRepository
from app.services.queue_monitoring_service import RabbitMQQueueMonitoringService


class MonitoringService:
    def __init__(
        self,
        repository: MonitoringRepository,
        queue_monitor: RabbitMQQueueMonitoringService | None = None,
    ) -> None:
        self.repository = repository
        self.queue_monitor = queue_monitor or RabbitMQQueueMonitoringService()

    def render_prometheus_metrics(self) -> str:
        snapshot = self.repository.load_snapshot()
        queue_snapshot = self.queue_monitor.load_snapshot()
        lines: list[str] = []

        _append_gauge(
            lines,
            "uav_dag_nodes_total",
            "Current number of registered nodes.",
            snapshot.node_count,
        )
        _append_labeled_gauge(
            lines,
            "uav_dag_nodes_by_type_total",
            "Current number of registered nodes grouped by node type.",
            "node_type",
            snapshot.nodes_by_type,
        )
        _append_labeled_gauge(
            lines,
            "uav_dag_nodes_by_status_total",
            "Current number of registered nodes grouped by status.",
            "status",
            snapshot.nodes_by_status,
        )

        _append_gauge(
            lines,
            "uav_dag_tasks_total",
            "Current number of DAG tasks.",
            snapshot.task_count,
        )
        _append_labeled_gauge(
            lines,
            "uav_dag_tasks_by_status_total",
            "Current number of DAG tasks grouped by status.",
            "status",
            snapshot.tasks_by_status,
        )

        _append_gauge(
            lines,
            "uav_dag_subtasks_total",
            "Current number of DAG subtasks.",
            snapshot.subtask_count,
        )
        _append_labeled_gauge(
            lines,
            "uav_dag_subtasks_by_status_total",
            "Current number of DAG subtasks grouped by status.",
            "status",
            snapshot.subtasks_by_status,
        )

        _append_gauge(
            lines,
            "uav_dag_schedule_plans_total",
            "Current number of schedule plans.",
            snapshot.schedule_plan_count,
        )
        _append_labeled_gauge(
            lines,
            "uav_dag_schedule_plans_by_status_total",
            "Current number of schedule plans grouped by status.",
            "status",
            snapshot.schedule_plans_by_status,
        )

        _append_gauge(
            lines,
            "uav_dag_executions_total",
            "Current number of execution records.",
            snapshot.execution_count,
        )
        _append_labeled_gauge(
            lines,
            "uav_dag_executions_by_status_total",
            "Current number of execution records grouped by status.",
            "status",
            snapshot.executions_by_status,
        )
        _append_gauge(
            lines,
            "uav_dag_execution_duration_ms_sum",
            "Sum of recorded execution durations in milliseconds.",
            snapshot.execution_duration_sum_ms,
        )
        _append_gauge(
            lines,
            "uav_dag_execution_duration_ms_count",
            "Number of execution records that have duration values.",
            snapshot.execution_duration_count,
        )
        _append_gauge(
            lines,
            "uav_dag_worker_auto_enqueue_enabled",
            "Whether API requests automatically enqueue execution records to Celery.",
            int(self.queue_monitor.settings.execution_auto_enqueue_enabled),
        )
        _append_gauge(
            lines,
            "uav_dag_worker_retry_max_retries",
            "Configured maximum Celery retries for execution worker tasks.",
            self.queue_monitor.settings.celery_execution_max_retries,
        )
        _append_gauge(
            lines,
            "uav_dag_worker_retry_backoff_seconds",
            "Configured base retry backoff for execution worker tasks.",
            self.queue_monitor.settings.celery_execution_retry_backoff_seconds,
        )
        _append_gauge(
            lines,
            "uav_dag_worker_retry_backoff_max_seconds",
            "Configured maximum retry backoff for execution worker tasks.",
            self.queue_monitor.settings.celery_execution_retry_backoff_max_seconds,
        )
        _append_labeled_gauge(
            lines,
            "uav_dag_queue_monitor_enabled",
            "Whether RabbitMQ queue monitoring is enabled.",
            "queue",
            {queue_snapshot.queue_name: int(queue_snapshot.enabled)},
        )
        _append_labeled_gauge(
            lines,
            "uav_dag_queue_monitor_available",
            "Whether RabbitMQ queue monitoring is currently reachable.",
            "queue",
            {queue_snapshot.queue_name: int(queue_snapshot.available)},
        )
        _append_labeled_gauge(
            lines,
            "uav_dag_queue_messages",
            "Current RabbitMQ messages in the Celery execution queue.",
            "queue",
            {queue_snapshot.queue_name: queue_snapshot.messages},
        )
        _append_labeled_gauge(
            lines,
            "uav_dag_queue_messages_ready",
            "Current RabbitMQ ready messages in the Celery execution queue.",
            "queue",
            {queue_snapshot.queue_name: queue_snapshot.messages_ready},
        )
        _append_labeled_gauge(
            lines,
            "uav_dag_queue_messages_unacknowledged",
            "Current RabbitMQ unacknowledged messages in the Celery execution queue.",
            "queue",
            {queue_snapshot.queue_name: queue_snapshot.messages_unacknowledged},
        )
        _append_labeled_gauge(
            lines,
            "uav_dag_queue_consumers",
            "Current RabbitMQ consumers attached to the Celery execution queue.",
            "queue",
            {queue_snapshot.queue_name: queue_snapshot.consumers},
        )

        return "\n".join(lines) + "\n"


def _append_gauge(lines: list[str], name: str, help_text: str, value: int) -> None:
    lines.append(f"# HELP {name} {help_text}")
    lines.append(f"# TYPE {name} gauge")
    lines.append(f"{name} {value}")


def _append_labeled_gauge(
    lines: list[str],
    name: str,
    help_text: str,
    label_name: str,
    values: dict[str, int],
) -> None:
    lines.append(f"# HELP {name} {help_text}")
    lines.append(f"# TYPE {name} gauge")
    for label_value, count in sorted(values.items()):
        lines.append(f'{name}{{{label_name}="{_escape_label_value(label_value)}"}} {count}')


def _escape_label_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')
