from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "uav-dag-offload-platform"
    app_env: str = "local"
    app_debug: bool = True
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/uav_dag"
    redis_url: str = "redis://localhost:6379/0"
    heartbeat_timeout_seconds: int = 30
    default_scheduler_strategy: str = "greedy"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
