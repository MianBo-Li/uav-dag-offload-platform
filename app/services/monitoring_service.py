from app.repositories.monitoring_repository import MonitoringRepository
from app.services.queue_monitoring_service import RabbitMQQueueMonitoringService
from app.services.worker_alert_service import WorkerAlertService
from app.services.worker_heartbeat_service import WorkerHeartbeatService


class MonitoringService:
    def __init__(
        self,
        repository: MonitoringRepository,
        queue_monitor: RabbitMQQueueMonitoringService | None = None,
        worker_heartbeat_service: WorkerHeartbeatService | None = None,
        worker_alert_service: WorkerAlertService | None = None,
    ) -> None:
        self.repository = repository
        self.queue_monitor = queue_monitor or RabbitMQQueueMonitoringService()
        self.worker_heartbeat_service = worker_heartbeat_service or WorkerHeartbeatService(
            repository.db
        )
        self.worker_alert_service = worker_alert_service or WorkerAlertService(
            repository.db
        )

    def render_prometheus_metrics(self) -> str:
        snapshot = self.repository.load_snapshot()
        queue_snapshots = self.queue_monitor.load_snapshots()
        worker_snapshot = self.worker_heartbeat_service.load_snapshot()
        worker_alert_snapshot = self.worker_alert_service.load_snapshot()
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
        _append_gauge(
            lines,
            "uav_dag_worker_heartbeat_timeout_seconds",
            "Configured timeout for considering a worker heartbeat online.",
            self.worker_heartbeat_service.settings.worker_heartbeat_timeout_seconds,
        )
        _append_gauge(
            lines,
            "uav_dag_workers_total",
            "Current number of workers that have reported heartbeats.",
            worker_snapshot.total_workers,
        )
        _append_gauge(
            lines,
            "uav_dag_workers_online",
            "Current number of workers whose last heartbeat is within the timeout.",
            worker_snapshot.online_workers,
        )
        _append_gauge(
            lines,
            "uav_dag_worker_latest_seen_timestamp",
            "Latest worker heartbeat timestamp in Unix seconds.",
            worker_snapshot.latest_seen_timestamp,
        )
        _append_labeled_gauge(
            lines,
            "uav_dag_workers_by_status_total",
            "Current number of workers grouped by heartbeat status.",
            "status",
            worker_snapshot.workers_by_status,
        )
        _append_labeled_gauge(
            lines,
            "uav_dag_worker_alerts_total",
            "Current number of worker alerts grouped by alert type.",
            "alert_type",
            worker_alert_snapshot.alerts_by_type,
        )
        _append_labeled_gauge(
            lines,
            "uav_dag_queue_monitor_enabled",
            "Whether RabbitMQ queue monitoring is enabled.",
            "queue",
            {snapshot.queue_name: int(snapshot.enabled) for snapshot in queue_snapshots},
        )
        _append_labeled_gauge(
            lines,
            "uav_dag_queue_monitor_available",
            "Whether RabbitMQ queue monitoring is currently reachable.",
            "queue",
            {snapshot.queue_name: int(snapshot.available) for snapshot in queue_snapshots},
        )
        _append_labeled_gauge(
            lines,
            "uav_dag_queue_messages",
            "Current RabbitMQ messages in Celery queues.",
            "queue",
            {snapshot.queue_name: snapshot.messages for snapshot in queue_snapshots},
        )
        _append_labeled_gauge(
            lines,
            "uav_dag_queue_messages_ready",
            "Current RabbitMQ ready messages in Celery queues.",
            "queue",
            {snapshot.queue_name: snapshot.messages_ready for snapshot in queue_snapshots},
        )
        _append_labeled_gauge(
            lines,
            "uav_dag_queue_messages_unacknowledged",
            "Current RabbitMQ unacknowledged messages in Celery queues.",
            "queue",
            {
                snapshot.queue_name: snapshot.messages_unacknowledged
                for snapshot in queue_snapshots
            },
        )
        _append_labeled_gauge(
            lines,
            "uav_dag_queue_consumers",
            "Current RabbitMQ consumers attached to Celery queues.",
            "queue",
            {snapshot.queue_name: snapshot.consumers for snapshot in queue_snapshots},
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
