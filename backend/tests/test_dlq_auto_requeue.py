from __future__ import annotations

import json
import uuid

import pytest

from app.runtime.dlq import DeadLetterQueue
from app.services.task_queue import PriorityTaskQueue, TaskPriority


class FakeRedis:
    def __init__(self):
        self.data = {}

    def rpush(self, key, *values):
        self.data.setdefault(key, [])
        self.data[key].extend(values)
        return len(self.data[key])

    def llen(self, key):
        return len(self.data.get(key, []))

    def lrange(self, key, start, end):
        values = self.data.get(key, [])

        if end == -1:
            return values[start:]

        return values[start:end + 1]

    def pipeline(self):
        return FakePipeline(self)

    def zadd(self, key, mapping):
        self.data.setdefault(key, {})
        self.data[key].update(mapping)

    def zcard(self, key):
        return len(self.data.get(key, {}))

    def sadd(self, key, value):
        self.data.setdefault(key, set())
        self.data[key].add(value)

    def smembers(self, key):
        return self.data.get(key, set())

    def zrange(self, key, start, end):
        values = self.data.get(key, {})

        if not values:
            return []

        ordered = sorted(
            values.items(),
            key=lambda item: item[1],
        )

        selected = ordered[start:end + 1]

        return [item[0] for item in selected]

    def zrem(self, key, value):
        values = self.data.get(key, {})

        if value in values:
            del values[value]
            return 1

        return 0

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value

    def incr(self, key):
        current = int(self.data.get(key, 0))
        current += 1
        self.data[key] = current
        return current

    def scan_iter(self, match=None):
        for key in self.data:
            if match is None:
                yield key
            elif match.endswith("*"):
                prefix = match[:-1]
                if key.startswith(prefix):
                    yield key


class FakePipeline:
    def __init__(self, redis):
        self.redis = redis
        self.operations = []

    def delete(self, key):
        self.operations.append(("delete", key))

    def rpush(self, key, *values):
        self.operations.append(("rpush", key, values))

    def execute(self):
        for operation in self.operations:
            if operation[0] == "delete":
                self.redis.data.pop(operation[1], None)

            elif operation[0] == "rpush":
                key = operation[1]
                values = operation[2]

                self.redis.data.setdefault(key, [])
                self.redis.data[key].extend(values)

        self.operations.clear()


@pytest.fixture
def redis():
    return FakeRedis()


@pytest.fixture
def dlq(redis):
    return DeadLetterQueue(redis)


def create_failed_task(
    dlq: DeadLetterQueue,
    tenant_id: str = "tenant-auto-requeue",
    priority: str = "HIGH",
):
    task = {
        "task_id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "payload": {
            "task_type": "TEST_TASK",
            "priority": priority,
            "context": {
                "source": "auto-requeue-test",
                "important": True,
            },
            "data": {
                "message": "original task",
            },
        },
    }

    return dlq.add(
        task=task,
        reason="test_failure",
        retry_count=3,
    )


def test_auto_requeue_moves_failed_task_back_to_queue(
    redis,
    dlq,
):
    create_failed_task(dlq)

    queue = PriorityTaskQueue(redis)

    results = dlq.auto_requeue(
        queue=queue,
        limit=100,
    )

    assert len(results) == 1

    result = results[0]

    assert result["tenant_id"] == "tenant-auto-requeue"
    assert result["old_task_id"]
    assert result["new_task_id"]

    assert dlq.count() == 0

    assert queue.depth(
        "tenant-auto-requeue"
    ) == 1


def test_auto_requeue_preserves_task_payload(
    redis,
    dlq,
):
    entry = create_failed_task(dlq)

    queue = PriorityTaskQueue(redis)

    results = dlq.auto_requeue(
        queue=queue,
        limit=100,
    )

    assert len(results) == 1

    queued_task = queue.peek(
        "tenant-auto-requeue"
    )

    assert queued_task is not None

    assert queued_task["payload"]["task_type"] == "TEST_TASK"

    assert queued_task["payload"]["context"] == {
        "source": "auto-requeue-test",
        "important": True,
    }

    assert queued_task["payload"]["data"] == {
        "message": "original task",
    }


def test_auto_requeue_generates_new_task_id(
    redis,
    dlq,
):
    entry = create_failed_task(dlq)

    original_task_id = entry["task"]["task_id"]

    queue = PriorityTaskQueue(redis)

    results = dlq.auto_requeue(
        queue=queue,
        limit=100,
    )

    assert len(results) == 1

    assert results[0]["old_task_id"] == original_task_id
    assert results[0]["new_task_id"] != original_task_id


def test_auto_requeue_respects_limit(
    redis,
    dlq,
):
    create_failed_task(
        dlq,
        tenant_id="tenant-one",
    )

    create_failed_task(
        dlq,
        tenant_id="tenant-two",
    )

    create_failed_task(
        dlq,
        tenant_id="tenant-three",
    )

    queue = PriorityTaskQueue(redis)

    results = dlq.auto_requeue(
        queue=queue,
        limit=2,
    )

    assert len(results) == 2
    assert dlq.count() == 1


def test_auto_requeue_empty_dlq(
    redis,
    dlq,
):
    queue = PriorityTaskQueue(redis)

    results = dlq.auto_requeue(
        queue=queue,
        limit=100,
    )

    assert results == []
    assert dlq.count() == 0


def test_auto_requeue_invalid_priority_defaults_to_normal(
    redis,
    dlq,
):
    create_failed_task(
        dlq,
        priority="INVALID_PRIORITY",
    )

    queue = PriorityTaskQueue(redis)

    results = dlq.auto_requeue(
        queue=queue,
        limit=100,
    )

    assert len(results) == 1

    queued_task = queue.peek(
        "tenant-auto-requeue"
    )

    assert queued_task is not None
    assert queued_task["priority"] == "NORMAL"


def test_auto_requeue_zero_limit(
    redis,
    dlq,
):
    create_failed_task(dlq)

    queue = PriorityTaskQueue(redis)

    results = dlq.auto_requeue(
        queue=queue,
        limit=0,
    )

    assert results == []
    assert dlq.count() == 1
    assert queue.depth(
        "tenant-auto-requeue"
    ) == 0


def test_auto_requeue_multiple_tenants(
    redis,
    dlq,
):
    create_failed_task(
        dlq,
        tenant_id="tenant-a",
    )

    create_failed_task(
        dlq,
        tenant_id="tenant-b",
    )

    queue = PriorityTaskQueue(redis)

    results = dlq.auto_requeue(
        queue=queue,
        limit=100,
    )

    assert len(results) == 2

    assert queue.depth("tenant-a") == 1
    assert queue.depth("tenant-b") == 1
    assert dlq.count() == 0