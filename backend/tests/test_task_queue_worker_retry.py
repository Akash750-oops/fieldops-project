from unittest.mock import Mock, patch

import pytest

from app.runtime.retry import RetryDecision
from app.services.task_queue_worker import consume_task_queue


def make_task():
    return {
        "task_id": "task-123",
        "tenant_id": "tenant-1",
        "priority": "NORMAL",
        "created_at": 1234567890.0,
        "payload": {
            "task_type": "dispatch",
            "context": {
                "job_id": 42,
            },
        },
    }


@pytest.mark.parametrize(
    ("retry_count", "expected_delay", "expected_retry_count"),
    [
        (0, 1.0, 1),
        (1, 2.0, 2),
        (2, 4.0, 3),
    ],
)
def test_worker_retries_same_task_with_correct_backoff(
    retry_count,
    expected_delay,
    expected_retry_count,
):
    task = make_task()

    redis = Mock()
    ai_task = Mock()

    celery_task = consume_task_queue._get_current_object()

    retry_exception = RuntimeError("celery retry")

    with patch(
        "app.services.task_queue_worker.get_redis_client",
        return_value=redis,
    ), patch(
        "app.services.task_queue_worker.AITask",
        return_value=ai_task,
    ), patch(
        "app.services.task_queue_worker.ai_orchestrator.execute",
        side_effect=TimeoutError("request timed out"),
    ), patch(
        "app.services.task_queue_worker.RetryManager.evaluate",
        return_value=Mock(
            decision=RetryDecision.RETRY,
            retry_number=expected_retry_count,
            delay_seconds=expected_delay,
            reason="retryable_error",
        ),
    ), patch.object(
        celery_task,
        "retry",
        side_effect=retry_exception,
    ) as mock_retry:

        with pytest.raises(
            RuntimeError,
            match="celery retry",
        ):
            celery_task.run(
                task=task,
                retry_count=retry_count,
            )

    mock_retry.assert_called_once()

    call_kwargs = mock_retry.call_args.kwargs

    assert call_kwargs["args"] == [task]
    assert call_kwargs["kwargs"] == {
        "retry_count": expected_retry_count,
    }
    assert call_kwargs["countdown"] == expected_delay


def test_worker_does_not_dequeue_on_retry():
    task = make_task()

    redis = Mock()
    ai_task = Mock()

    celery_task = consume_task_queue._get_current_object()

    with patch(
        "app.services.task_queue_worker.get_redis_client",
        return_value=redis,
    ), patch(
        "app.services.task_queue_worker.AITask",
        return_value=ai_task,
    ), patch(
        "app.services.task_queue_worker.ai_orchestrator.execute",
        side_effect=TimeoutError("timeout"),
    ), patch(
        "app.services.task_queue_worker.RetryManager.evaluate",
        return_value=Mock(
            decision=RetryDecision.RETRY,
            retry_number=1,
            delay_seconds=1.0,
            reason="retryable_error",
        ),
    ), patch.object(
        celery_task,
        "retry",
        side_effect=RuntimeError("celery retry"),
    ):

        with pytest.raises(RuntimeError):
            celery_task.run(
                task=task,
                retry_count=0,
            )

    redis.zrange.assert_not_called()


def test_worker_sends_non_retryable_error_to_dlq():
    task = make_task()

    redis = Mock()
    celery_task = consume_task_queue._get_current_object()

    dlq_result = {
        "id": "dlq-123",
        "task": task,
        "reason": "non_retryable_error",
    }

    with patch(
        "app.services.task_queue_worker.get_redis_client",
        return_value=redis,
    ), patch(
        "app.services.task_queue_worker.AITask",
        return_value=Mock(),
    ), patch(
        "app.services.task_queue_worker.ai_orchestrator.execute",
        side_effect=ValueError("bad request"),
    ), patch(
        "app.services.task_queue_worker.RetryManager.evaluate",
        return_value=Mock(
            decision=RetryDecision.DLQ,
            retry_number=0,
            delay_seconds=0.0,
            reason="non_retryable_error",
        ),
    ), patch(
        "app.services.task_queue_worker._move_task_to_dlq",
        return_value={
            "task_id": "task-123",
            "success": False,
            "dlq_id": "dlq-123",
        },
    ) as mock_dlq:

        result = celery_task.run(
            task=task,
            retry_count=0,
        )

    mock_dlq.assert_called_once()

    assert result["success"] is False
    assert result["dlq_id"] == "dlq-123"


def test_worker_uses_same_task_after_retry():
    task = make_task()

    redis = Mock()
    celery_task = consume_task_queue._get_current_object()

    with patch(
        "app.services.task_queue_worker.get_redis_client",
        return_value=redis,
    ), patch(
        "app.services.task_queue_worker.AITask",
        return_value=Mock(),
    ), patch(
        "app.services.task_queue_worker.ai_orchestrator.execute",
        side_effect=TimeoutError("timeout"),
    ), patch(
        "app.services.task_queue_worker.RetryManager.evaluate",
        return_value=Mock(
            decision=RetryDecision.RETRY,
            retry_number=2,
            delay_seconds=2.0,
            reason="retryable_error",
        ),
    ), patch.object(
        celery_task,
        "retry",
        side_effect=RuntimeError("retry"),
    ) as mock_retry:

        with pytest.raises(RuntimeError):
            celery_task.run(
                task=task,
                retry_count=1,
            )

    retry_args = mock_retry.call_args.kwargs["args"]

    assert retry_args[0] is task
    assert retry_args[0]["task_id"] == "task-123"

    # The retry must not dequeue another task.
    redis.zrange.assert_not_called()