from sqlalchemy.exc import DBAPIError, OperationalError, TimeoutError as SQLAlchemyTimeoutError

from app.core.errors import AppError
from app.worker.tasks import (
    calculate_retry_countdown,
    has_worker_retry_budget,
    is_retryable_worker_exception,
    sleep_with_cancel_checks,
)


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


def test_worker_retry_budget_allows_retries_before_limit() -> None:
    assert has_worker_retry_budget(retry_count=0, max_retries=3) is True
    assert has_worker_retry_budget(retry_count=2, max_retries=3) is True
    assert has_worker_retry_budget(retry_count=3, max_retries=3) is False


def test_sleep_with_cancel_checks_returns_immediately_when_already_canceled() -> None:
    sleep_calls: list[float] = []

    assert sleep_with_cancel_checks(
        "execution-1",
        total_seconds=1.0,
        check_interval_seconds=0.2,
        sleep_fn=sleep_calls.append,
        cancel_check_fn=lambda _: True,
    )
    assert sleep_calls == []


def test_sleep_with_cancel_checks_splits_sleep_and_stops_after_cancel() -> None:
    sleep_calls: list[float] = []
    check_count = 0

    def cancel_after_two_checks(_: object) -> bool:
        nonlocal check_count
        check_count += 1
        return check_count >= 3

    assert sleep_with_cancel_checks(
        "execution-1",
        total_seconds=1.0,
        check_interval_seconds=0.25,
        sleep_fn=sleep_calls.append,
        cancel_check_fn=cancel_after_two_checks,
    )
    assert sleep_calls == [0.25, 0.25]
