import json

from app.runtime.dlq import DeadLetterQueue


class FakeRedis:
    def __init__(self):
        self.data = []

    def rpush(self, key, *values):
        self.data.extend(values)
        return len(self.data)

    def llen(self, key):
        return len(self.data)

    def lrange(self, key, start, end):
        if end == -1:
            return self.data[start:]

        return self.data[start:end + 1]

    def pipeline(self):
        return FakePipeline(self)


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
                self.redis.data.clear()

            elif operation[0] == "rpush":
                self.redis.data.extend(operation[2])


def create_task():
    return {
        "task_id": "task-123",
        "tenant_id": "tenant-1",
        "priority": "HIGH",
        "created_at": 1234567890.0,
        "payload": {
            "task_type": "dispatch",
            "context": {
                "job_id": "job-123",
                "customer_id": "customer-123",
            },
        },
    }


def test_add_stores_full_task_context():
    redis = FakeRedis()
    dlq = DeadLetterQueue(redis)

    error = TimeoutError("request timed out")

    entry = dlq.add(
        task=create_task(),
        reason="retryable_error",
        retry_count=3,
        error=error,
    )

    assert entry["task"]["task_id"] == "task-123"
    assert entry["task"]["tenant_id"] == "tenant-1"
    assert entry["task"]["payload"]["task_type"] == "dispatch"
    assert entry["retry_count"] == 3
    assert entry["error_type"] == "TimeoutError"
    assert entry["error_message"] == "request timed out"
    assert entry["reason"] == "retryable_error"


def test_count_returns_dlq_size():
    redis = FakeRedis()
    dlq = DeadLetterQueue(redis)

    dlq.add(create_task(), "failure-1")
    dlq.add(create_task(), "failure-2")

    assert dlq.count() == 2


def test_list_returns_items():
    redis = FakeRedis()
    dlq = DeadLetterQueue(redis)

    first = dlq.add(
        create_task(),
        "first_failure",
    )

    second = dlq.add(
        create_task(),
        "second_failure",
    )

    items = dlq.list()

    assert len(items) == 2
    assert items[0]["id"] == first["id"]
    assert items[1]["id"] == second["id"]


def test_list_supports_limit():
    redis = FakeRedis()
    dlq = DeadLetterQueue(redis)

    dlq.add(create_task(), "failure-1")
    dlq.add(create_task(), "failure-2")
    dlq.add(create_task(), "failure-3")

    items = dlq.list(limit=2)

    assert len(items) == 2


def test_get_returns_matching_item():
    redis = FakeRedis()
    dlq = DeadLetterQueue(redis)

    entry = dlq.add(
        create_task(),
        "failure",
    )

    result = dlq.get(entry["id"])

    assert result is not None
    assert result["id"] == entry["id"]


def test_get_returns_none_for_unknown_id():
    redis = FakeRedis()
    dlq = DeadLetterQueue(redis)

    assert dlq.get("does-not-exist") is None


def test_delete_removes_item():
    redis = FakeRedis()
    dlq = DeadLetterQueue(redis)

    first = dlq.add(
        create_task(),
        "failure-1",
    )

    second = dlq.add(
        create_task(),
        "failure-2",
    )

    assert dlq.delete(first["id"]) is True
    assert dlq.count() == 1

    remaining = dlq.list()

    assert remaining[0]["id"] == second["id"]


def test_delete_unknown_item_returns_false():
    redis = FakeRedis()
    dlq = DeadLetterQueue(redis)

    assert dlq.delete("unknown") is False


def test_requeue_payload_returns_original_task():
    redis = FakeRedis()
    dlq = DeadLetterQueue(redis)

    task = create_task()

    entry = dlq.add(
        task,
        "permanent_failure",
        retry_count=3,
    )

    payload = dlq.requeue_payload(
        entry["id"]
    )

    assert payload == task


def test_requeue_payload_unknown_id_returns_none():
    redis = FakeRedis()
    dlq = DeadLetterQueue(redis)

    assert dlq.requeue_payload(
        "unknown"
    ) is None

def test_add_persists_to_postgresql():
    class FakeDB:
        def __init__(self):
            self.added = []
            self.flushed = False

        def add(self, item):
            self.added.append(item)

        def flush(self):
            self.flushed = True

    redis = FakeRedis()
    db = FakeDB()

    dlq = DeadLetterQueue(
        redis,
        db,
    )

    task = create_task()

    entry = dlq.add(
        task=task,
        reason="maximum_retries_exceeded",
        retry_count=3,
        error=TimeoutError("request timed out"),
    )

    assert len(db.added) == 1
    assert db.flushed is True

    database_entry = db.added[0]

    assert database_entry.id == entry["id"]
    assert database_entry.task_id == "task-123"
    assert database_entry.tenant_id == "tenant-1"
    assert database_entry.task_type == "dispatch"
    assert database_entry.retry_count == 3
    assert database_entry.reason == "maximum_retries_exceeded"
    assert database_entry.error_type == "TimeoutError"
    assert database_entry.error_message == "request timed out"


def test_add_requires_tenant_id_for_database_persistence():
    class FakeDB:
        def add(self, item):
            pass

        def flush(self):
            pass

    redis = FakeRedis()
    db = FakeDB()

    dlq = DeadLetterQueue(
        redis,
        db,
    )

    task = create_task()
    task["tenant_id"] = None

    try:
        dlq.add(
            task=task,
            reason="permanent_failure",
        )
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "tenant_id is required" in str(exc)


def test_alert_threshold():
    redis = FakeRedis()
    dlq = DeadLetterQueue(redis)

    for _ in range(10):
        dlq.add(
            create_task(),
            "failure",
        )

    assert dlq.is_above_alert_threshold(10) is False

    dlq.add(
        create_task(),
        "failure",
    )

    assert dlq.is_above_alert_threshold(10) is True