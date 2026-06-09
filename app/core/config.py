from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "uav-dag-offload-platform"
    app_env: str = "local"
    app_debug: bool = True
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/uav_dag"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "amqp://guest:guest@localhost:5672//"
    celery_result_backend: str = "redis://localhost:6379/1"
    celery_task_default_queue: str = "uav_dag_execution"
    celery_execution_max_retries: int = 3
    celery_execution_retry_backoff_seconds: int = 5
    celery_execution_retry_backoff_max_seconds: int = 60
    rabbitmq_queue_monitoring_enabled: bool = False
    rabbitmq_management_url: str = "http://localhost:15672/api"
    rabbitmq_management_username: str = "guest"
    rabbitmq_management_password: str = "guest"
    rabbitmq_management_vhost: str = "/"
    rabbitmq_management_timeout_seconds: float = 1.0
    execution_auto_enqueue_enabled: bool = False
    simulated_execution_duration_ms: int = 100
    simulated_execution_sleep_seconds: float = 0.0
    heartbeat_timeout_seconds: int = 30
    default_scheduler_strategy: str = "greedy"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
