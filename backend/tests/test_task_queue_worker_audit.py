from unittest.mock import Mock, patch

import pytest

from app.runtime.retry import RetryDecision
from app.services.task_queue_worker import consume_task_queue


def make_task():
    return {
        "task_id": "task-audit-123",
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


def test_retry_creates_task_retry_audit():
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
        side_effect=TimeoutError("request timed out"),
    ), patch(
        "app.services.task_queue_worker.RetryManager.evaluate",
        return_value=Mock(
            decision=RetryDecision.RETRY,
            retry_number=1,
            delay_seconds=1.0,
            reason="retryable_error",
        ),
    ), patch(
        "app.services.task_queue_worker.audit_log"
    ) as mock_audit, patch.object(
        celery_task,
        "retry",
        side_effect=RuntimeError("celery retry"),
    ):

        with pytest.raises(RuntimeError, match="celery retry"):
            celery_task.run(
                task=task,
                retry_count=0,
            )

    mock_audit.assert_called_once()

    audit_kwargs = mock_audit.call_args.kwargs

    assert audit_kwargs["action"] == "TASK_RETRY"
    assert audit_kwargs["tenant_id"] == "tenant-1"
    assert audit_kwargs["entity_type"] == "task"
    assert audit_kwargs["entity_id"] == "task-audit-123"

    details = audit_kwargs["details"]

    assert details["retry_number"] == 1
    assert details["retry_delay_seconds"] == 1.0
    assert details["reason"] == "retryable_error"
    assert details["error_type"] == "TimeoutError"
    assert details["error_message"] == "request timed out"


def test_retry_audit_is_committed_before_celery_retry():
    task = make_task()

    redis = Mock()
    celery_task = consume_task_queue._get_current_object()

    db = Mock()

    call_order = []

    db.commit.side_effect = lambda: call_order.append("commit")

    def fake_retry(**kwargs):
        call_order.append("retry")
        raise RuntimeError("celery retry")

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
            retry_number=1,
            delay_seconds=1.0,
            reason="retryable_error",
        ),
    ), patch(
        "app.services.task_queue_worker.SessionLocal",
        return_value=db,
    ), patch(
        "app.services.task_queue_worker.audit_log"
    ), patch.object(
        celery_task,
        "retry",
        side_effect=fake_retry,
    ):

        with pytest.raises(RuntimeError, match="celery retry"):
            celery_task.run(
                task=task,
                retry_count=0,
            )

    assert call_order == ["commit", "retry"]
    db.close.assert_called_once()


def test_dlq_creates_task_dlq_audit():
    task = make_task()

    redis = Mock()

    dlq_entry = {
        "id": "dlq-audit-123",
        "task": task,
        "reason": "maximum_retries_exceeded",
        "retry_count": 3,
    }

    db = Mock()

    error = TimeoutError("upstream service timed out")

    with patch(
        "app.services.task_queue_worker.get_redis_client",
        return_value=redis,
    ), patch(
        "app.services.task_queue_worker.AITask",
        return_value=Mock(),
    ), patch(
        "app.services.task_queue_worker.ai_orchestrator.execute",
        side_effect=error,
    ), patch(
        "app.services.task_queue_worker.RetryManager.evaluate",
        return_value=Mock(
            decision=RetryDecision.DLQ,
            retry_number=3,
            delay_seconds=0.0,
            reason="maximum_retries_exceeded",
        ),
    ), patch(
        "app.services.task_queue_worker.SessionLocal",
        return_value=db,
    ), patch(
        "app.services.task_queue_worker.DeadLetterQueue.add",
        return_value=dlq_entry,
    ), patch(
        "app.services.task_queue_worker.audit_log"
    ) as mock_audit:

        result = consume_task_queue.run(
            task=task,
            retry_count=3,
        )

    mock_audit.assert_called_once()

    audit_kwargs = mock_audit.call_args.kwargs

    assert audit_kwargs["action"] == "TASK_DLQ"
    assert audit_kwargs["tenant_id"] == "tenant-1"
    assert audit_kwargs["entity_type"] == "task"
    assert audit_kwargs["entity_id"] == "task-audit-123"

    details = audit_kwargs["details"]

    assert details["dlq_id"] == "dlq-audit-123"
    assert details["reason"] == "maximum_retries_exceeded"
    assert details["retry_count"] == 3
    assert details["error_type"] == "TimeoutError"
    assert details["error_message"] == "upstream service timed out"

    db.commit.assert_called_once()
    db.close.assert_called_once()

    assert result["success"] is False
    assert result["dlq_id"] == "dlq-audit-123"