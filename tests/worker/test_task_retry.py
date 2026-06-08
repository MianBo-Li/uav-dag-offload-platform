from sqlalchemy.exc import DBAPIError, OperationalError, TimeoutError as SQLAlchemyTimeoutError

from app.core.errors import AppError
from app.worker.tasks import calculate_retry_countdown, is_retryable_worker_exception


def test_worker_retries_database_operational_errors() -> None:
    error = OperationalError("select 1", {}, Exception("database unavailable"))

    assert is_retryable_worker_exception(error) is True


def test_worker_retries_sqlalchemy_timeout_errors() -> None:
    error = SQLAlchemyTimeoutError("connection pool timeout")

    assert is_retryable_worker_exception(error) is True


def test_worker_retries_invalidated_dbapi_connection() -> None:
    error = DBAPIError.instance(
        "select 1",
        {},
        Exception("connection dropped"),
        Exception,
        connection_invalidated=True,
    )

    assert is_retryable_worker_exception(error) is True


def test_worker_does_not_retry_business_errors() -> None:
    error = AppError(
        code="EXECUTION_NOT_FOUND",
        message="Execution record not found",
        status_code=404,
    )

    assert is_retryable_worker_exception(error) is False


def test_worker_does_not_retry_validation_errors() -> None:
    assert is_retryable_worker_exception(ValueError("bad result status")) is False


def test_retry_countdown_uses_exponential_backoff_with_cap() -> None:
    assert calculate_retry_countdown(
        retry_count=0,
        base_seconds=5,
        max_seconds=60,
    ) == 5
    assert calculate_retry_countdown(
        retry_count=1,
        base_seconds=5,
        max_seconds=60,
    ) == 10
    assert calculate_retry_countdown(
        retry_count=4,
        base_seconds=5,
        max_seconds=60,
    ) == 60
