import pytest

from app.runtime.retry import (
    RetryDecision,
    RetryManager,
)


class HTTPError(Exception):
    def __init__(self, status_code: int):
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}")


class GuardrailViolationError(Exception):
    pass


def test_backoff_retry_1():
    assert RetryManager.calculate_backoff(1) == 1.0


def test_backoff_retry_2():
    assert RetryManager.calculate_backoff(2) == 2.0


def test_backoff_retry_3():
    assert RetryManager.calculate_backoff(3) == 4.0


def test_backoff_rejects_invalid_retry_number():
    with pytest.raises(ValueError):
        RetryManager.calculate_backoff(0)

    with pytest.raises(ValueError):
        RetryManager.calculate_backoff(4)


@pytest.mark.parametrize(
    "status_code",
    [
        429,
        500,
        501,
        502,
        503,
        504,
        599,
    ],
)
def test_retryable_http_errors(status_code):
    error = HTTPError(status_code)

    assert RetryManager.is_retryable(error) is True


@pytest.mark.parametrize(
    "status_code",
    [
        400,
        401,
        403,
    ],
)
def test_non_retryable_http_errors(status_code):
    error = HTTPError(status_code)

    assert RetryManager.is_retryable(error) is False


def test_timeout_is_retryable():
    error = TimeoutError("request timed out")

    assert RetryManager.is_retryable(error) is True


def test_connection_error_is_retryable():
    error = ConnectionError("connection failed")

    assert RetryManager.is_retryable(error) is True


def test_guardrail_violation_is_not_retryable():
    error = GuardrailViolationError(
        "guardrail violation detected"
    )

    assert RetryManager.is_retryable(error) is False


def test_retry_one():
    result = RetryManager.evaluate(
        HTTPError(503),
        retry_count=0,
    )

    assert result.decision == RetryDecision.RETRY
    assert result.retry_number == 1
    assert result.delay_seconds == 1.0


def test_retry_two():
    result = RetryManager.evaluate(
        HTTPError(503),
        retry_count=1,
    )

    assert result.decision == RetryDecision.RETRY
    assert result.retry_number == 2
    assert result.delay_seconds == 2.0


def test_retry_three():
    result = RetryManager.evaluate(
        HTTPError(503),
        retry_count=2,
    )

    assert result.decision == RetryDecision.RETRY
    assert result.retry_number == 3
    assert result.delay_seconds == 4.0


def test_max_retries_goes_to_dlq():
    result = RetryManager.evaluate(
        HTTPError(503),
        retry_count=3,
    )

    assert result.decision == RetryDecision.DLQ
    assert result.delay_seconds == 0.0
    assert result.reason == "maximum_retries_exceeded"


@pytest.mark.parametrize(
    "error",
    [
        HTTPError(400),
        HTTPError(401),
        HTTPError(403),
        GuardrailViolationError(
            "guardrail violation"
        ),
    ],
)
def test_non_retryable_errors_go_directly_to_dlq(error):
    result = RetryManager.evaluate(
        error,
        retry_count=0,
    )

    assert result.decision == RetryDecision.DLQ

def test_consume_task_queue_is_registered_with_celery():
    from app.services.task_queue_worker import consume_task_queue

    assert consume_task_queue.name == "app.tasks.consume_task_queue"