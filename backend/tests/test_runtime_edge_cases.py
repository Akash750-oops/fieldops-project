from __future__ import annotations

import json

import pytest

from app.runtime.dlq import DeadLetterQueue
from app.runtime.retry import RetryDecision, RetryManager


# ==========================================================
# RetryManager edge-case coverage
# ==========================================================


def test_extract_status_code_from_response():
    class Response:
        status_code = 503

    class Error(Exception):
        response = Response()

    error = Error()

    assert RetryManager.extract_status_code(error) == 503


def test_extract_status_code_returns_none_for_invalid_values():
    class Error(Exception):
        status_code = "503"

    assert RetryManager.extract_status_code(Error()) is None


def test_extract_status_code_returns_none_without_status():
    assert RetryManager.extract_status_code(Exception("failure")) is None


def test_guardrail_violation_by_class_name():
    class GuardrailViolation(Exception):
        pass

    assert RetryManager.is_guardrail_violation(
        GuardrailViolation("blocked")
    ) is True


def test_guardrail_violation_by_message():
    error = Exception("Guardrail violation detected")

    assert RetryManager.is_guardrail_violation(error) is True


def test_unknown_error_is_not_retryable():
    error = RuntimeError("unexpected failure")

    assert RetryManager.is_retryable(error) is False


def test_other_4xx_error_is_not_retryable():
    class Error(Exception):
        status_code = 404

    assert RetryManager.is_retryable(Error()) is False


def test_should_retry_stops_after_max_retries():
    error = TimeoutError("timeout")

    assert RetryManager.should_retry(
        error,
        RetryManager.MAX_RETRIES,
    ) is False


def test_should_retry_returns_true_for_transient_error():
    error = TimeoutError("timeout")

    assert RetryManager.should_retry(
        error,
        0,
    ) is True


def test_evaluate_non_retryable_error_goes_to_dlq():
    result = RetryManager.evaluate(
        RuntimeError("permanent failure"),
        0,
    )

    assert result.decision == RetryDecision.DLQ
    assert result.reason == "non_retryable_error"
    assert result.delay_seconds == 0.0


def test_evaluate_max_retries_goes_to_dlq():
    result = RetryManager.evaluate(
        TimeoutError("timeout"),
        RetryManager.MAX_RETRIES,
    )

    assert result.decision == RetryDecision.DLQ
    assert result.reason == "maximum_retries_exceeded"
    assert result.delay_seconds == 0.0


def test_retry_policy_returns_expected_configuration():
    policy = RetryManager.policy()

    assert policy["max_retries"] == 3
    assert policy["backoff_delays"] == [1.0, 2.0, 4.0]
    assert 429 in policy["retryable_status_codes"]
    assert 400 in policy["non_retryable_status_codes"]


# ==========================================================
# DLQ edge-case coverage
# ==========================================================


class FakePipeline:
    def __init__(self, redis):
        self.redis = redis
        self.commands = []

    def delete(self, key):
        self.commands.append(("delete", key))
        return self

    def rpush(self, key, *values):
        self.commands.append(("rpush", key, *values))
        return self

    def execute(self):
        for command in self.commands:
            if command[0] == "delete":
                self.redis.data.pop(command[1], None)

            elif command[0] == "rpush":
                key = command[1]
                values = command[2:]

                self.redis.data.setdefault(key, [])
                self.redis.data[key].extend(values)

        return []


class FakeRedis:
    def __init__(self):
        self.data = {}

    def rpush(self, key, *values):
        self.data.setdefault(key, [])
        self.data[key].extend(values)

    def llen(self, key):
        return len(self.data.get(key, []))

    def lrange(self, key, start, end):
        items = self.data.get(key, [])

        if end == -1:
            return items[start:]

        return items[start:end + 1]

    def pipeline(self):
        return FakePipeline(self)


class FakeQueue:
    def __init__(self):
        self.calls = []

    def enqueue(self, task, priority, tenant_id):
        self.calls.append(
            {
                "task": task,
                "priority": priority,
                "tenant_id": tenant_id,
            }
        )

        return "new-task-id"


def make_task(
    tenant_id="tenant-1",
    priority="NORMAL",
):
    return {
        "task_id": "old-task-id",
        "tenant_id": tenant_id,
        "payload": {
            "task_type": "TEST_TASK",
            "priority": priority,
            "context": {
                "source": "test",
            },
        },
    }


def test_dlq_list_decodes_bytes():
    redis = FakeRedis()

    task = make_task()

    entry = {
        "id": "dlq-1",
        "task": task,
        "reason": "failure",
        "retry_count": 3,
        "status": "FAILED",
    }

    redis.rpush(
        DeadLetterQueue.DLQ_KEY,
        json.dumps(entry).encode("utf-8"),
    )

    dlq = DeadLetterQueue(redis)

    items = dlq.list()

    assert len(items) == 1
    assert items[0]["id"] == "dlq-1"


def test_dlq_get_failed_items_zero_limit():
    redis = FakeRedis()
    dlq = DeadLetterQueue(redis)

    assert dlq.get_failed_items(0) == []


def test_dlq_get_failed_items_filters_non_failed_items():
    redis = FakeRedis()

    failed = {
        "id": "failed",
        "status": "FAILED",
    }

    requeued = {
        "id": "requeued",
        "status": "REQUEUED",
    }

    redis.rpush(
        DeadLetterQueue.DLQ_KEY,
        json.dumps(failed),
        json.dumps(requeued),
    )

    dlq = DeadLetterQueue(redis)

    items = dlq.get_failed_items()

    assert len(items) == 1
    assert items[0]["id"] == "failed"


def test_dlq_auto_requeue_skips_invalid_task():
    redis = FakeRedis()

    redis.rpush(
        DeadLetterQueue.DLQ_KEY,
        json.dumps(
            {
                "id": "invalid-task",
                "status": "FAILED",
                "task": "not-a-dict",
            }
        ),
    )

    dlq = DeadLetterQueue(redis)
    queue = FakeQueue()

    result = dlq.auto_requeue(queue)

    assert result == []
    assert queue.calls == []


def test_dlq_auto_requeue_skips_task_without_tenant():
    redis = FakeRedis()

    redis.rpush(
        DeadLetterQueue.DLQ_KEY,
        json.dumps(
            {
                "id": "missing-tenant",
                "status": "FAILED",
                "task": {
                    "task_id": "task-1",
                    "payload": {},
                },
            }
        ),
    )

    dlq = DeadLetterQueue(redis)
    queue = FakeQueue()

    result = dlq.auto_requeue(queue)

    assert result == []
    assert queue.calls == []


def test_dlq_auto_requeue_queue_failure_keeps_dlq_item():
    redis = FakeRedis()

    redis.rpush(
        DeadLetterQueue.DLQ_KEY,
        json.dumps(
            {
                "id": "queue-failure",
                "status": "FAILED",
                "task": make_task(),
            }
        ),
    )

    class FailingQueue:
        def enqueue(self, task, priority, tenant_id):
            raise RuntimeError("queue unavailable")

    dlq = DeadLetterQueue(redis)

    result = dlq.auto_requeue(
        FailingQueue()
    )

    assert result == []
    assert dlq.get("queue-failure") is not None


def test_dlq_auto_requeue_invalid_priority_uses_normal():
    redis = FakeRedis()

    redis.rpush(
        DeadLetterQueue.DLQ_KEY,
        json.dumps(
            {
                "id": "invalid-priority",
                "status": "FAILED",
                "task": make_task(priority="INVALID"),
            }
        ),
    )

    dlq = DeadLetterQueue(redis)
    queue = FakeQueue()

    result = dlq.auto_requeue(queue)

    assert len(result) == 1
    assert queue.calls[0]["priority"].name == "NORMAL"


def test_dlq_auto_requeue_missing_dlq_id_skips_result():
    redis = FakeRedis()

    redis.rpush(
        DeadLetterQueue.DLQ_KEY,
        json.dumps(
            {
                "status": "FAILED",
                "task": make_task(),
            }
        ),
    )

    dlq = DeadLetterQueue(redis)
    queue = FakeQueue()

    result = dlq.auto_requeue(queue)

    assert result == []


def test_dlq_auto_requeue_zero_limit():
    redis = FakeRedis()
    dlq = DeadLetterQueue(redis)
    queue = FakeQueue()

    assert dlq.auto_requeue(queue, limit=0) == []


def test_dlq_auto_requeue_preserves_item_when_delete_fails():
    redis = FakeRedis()

    redis.rpush(
        DeadLetterQueue.DLQ_KEY,
        json.dumps(
            {
                "id": "delete-failure",
                "status": "FAILED",
                "task": make_task(),
            }
        ),
    )

    class DeleteFailingDLQ(DeadLetterQueue):
        def delete(self, dlq_id):
            return False

    dlq = DeleteFailingDLQ(redis)
    queue = FakeQueue()

    result = dlq.auto_requeue(queue)

    assert result == []
    assert dlq.get("delete-failure") is not None

def test_dlq_list_with_explicit_positive_limit():
    redis = FakeRedis()

    entries = [
        {
            "id": "dlq-1",
            "status": "FAILED",
        },
        {
            "id": "dlq-2",
            "status": "FAILED",
        },
        {
            "id": "dlq-3",
            "status": "FAILED",
        },
    ]

    for entry in entries:
        redis.rpush(
            DeadLetterQueue.DLQ_KEY,
            json.dumps(entry),
        )

    dlq = DeadLetterQueue(redis)

    items = dlq.list(limit=2)

    assert len(items) == 2
    assert items[0]["id"] == "dlq-1"
    assert items[1]["id"] == "dlq-2"

def test_dlq_list_zero_limit_returns_empty():
    redis = FakeRedis()

    redis.rpush(
        DeadLetterQueue.DLQ_KEY,
        json.dumps(
            {
                "id": "dlq-1",
                "status": "FAILED",
            }
        ),
    )

    dlq = DeadLetterQueue(redis)

    result = dlq.list(limit=0)

    assert result == []