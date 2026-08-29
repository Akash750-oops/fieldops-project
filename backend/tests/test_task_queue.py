import fakeredis
import json
from app.services.task_queue import (
    PriorityTaskQueue,
    TaskPriority,
    QueueBackpressureError,
)
import app.redis_client
import app.tasks
import app.services.task_queue_worker

def test_priority_ordering():
    redis = fakeredis.FakeRedis(decode_responses=True)
    queue = PriorityTaskQueue(redis)

    queue.enqueue(
        {"message": "low task"},
        TaskPriority.LOW,
        "tenant-a",
    )

    queue.enqueue(
        {"message": "critical task"},
        TaskPriority.CRITICAL,
        "tenant-a",
    )

    queue.enqueue(
        {"message": "normal task"},
        TaskPriority.NORMAL,
        "tenant-a",
    )

    queue.enqueue(
        {"message": "high task"},
        TaskPriority.HIGH,
        "tenant-a",
    )

    task = queue.peek("tenant-a")

    assert task is not None
    assert task["priority"] == "CRITICAL"

def test_round_robin_fairness():
    redis = fakeredis.FakeRedis(decode_responses=True)
    queue = PriorityTaskQueue(redis)

    queue.enqueue(
        {"message": "A1"},
        TaskPriority.NORMAL,
        "tenant-a",
    )

    queue.enqueue(
        {"message": "A2"},
        TaskPriority.NORMAL,
        "tenant-a",
    )

    queue.enqueue(
        {"message": "B1"},
        TaskPriority.NORMAL,
        "tenant-b",
    )

    queue.enqueue(
        {"message": "C1"},
        TaskPriority.NORMAL,
        "tenant-c",
    )

    first = queue.dequeue()
    second = queue.dequeue()
    third = queue.dequeue()

    assert first["tenant_id"] == "tenant-a"
    assert second["tenant_id"] == "tenant-b"
    assert third["tenant_id"] == "tenant-c"


def test_move_task_to_dlq():
    redis = fakeredis.FakeRedis(decode_responses=True)
    queue = PriorityTaskQueue(redis)

    task = {
        "task_id": "task-1",
        "message": "failed task",
    }

    queue.move_to_dlq(
        task,
        "maximum retries exceeded",
    )

    dlq_items = redis.lrange(
        queue.DLQ_KEY,
        0,
        -1,
    )

    assert len(dlq_items) == 1

    dlq_entry = json.loads(dlq_items[0])

    assert dlq_entry["task"] == task
    assert dlq_entry["reason"] == "maximum retries exceeded"
    assert "moved_at" in dlq_entry


def test_backpressure_threshold():
    redis = fakeredis.FakeRedis(decode_responses=True)
    queue = PriorityTaskQueue(redis)

    assert queue.is_backpressured("tenant-a") is False

    redis.zadd(
        queue._queue_key("tenant-a"),
        {
            f"task-{i}": float(i)
            for i in range(10_001)
        },
    )

    assert queue.total_depth() == 10_001
    assert queue.is_backpressured("tenant-a") is True

    try:
        queue.enqueue(
            {"message": "blocked task"},
            TaskPriority.NORMAL,
            "tenant-a",
        )
        assert False, "Expected QueueBackpressureError"
    except QueueBackpressureError:
        pass

def test_queue_stats():
    redis = fakeredis.FakeRedis(decode_responses=True)
    queue = PriorityTaskQueue(redis)

    queue.enqueue(
        {"message": "task-1"},
        TaskPriority.NORMAL,
        "tenant-a",
    )

    stats = queue.stats("tenant-a")

    assert stats["depth"] == 1
    assert stats["oldest_task_age"] >= 0
    assert stats["throughput"] == 0

def test_throughput_counts_dequeued_tasks():
    redis = fakeredis.FakeRedis(decode_responses=True)
    queue = PriorityTaskQueue(redis)

    queue.enqueue(
        {"message": "task-1"},
        TaskPriority.NORMAL,
        "tenant-a",
    )

    queue.enqueue(
        {"message": "task-2"},
        TaskPriority.NORMAL,
        "tenant-a",
    )

    assert queue.throughput() == 0

    queue.dequeue()

    assert queue.throughput() == 1

    queue.dequeue()

    assert queue.throughput() == 2


def test_priority_wins_over_tenant_rotation():
    redis = fakeredis.FakeRedis(decode_responses=True)
    queue = PriorityTaskQueue(redis)

    queue.enqueue(
        {"message": "low task"},
        TaskPriority.LOW,
        "tenant-a",
    )

    queue.enqueue(
        {"message": "critical task"},
        TaskPriority.CRITICAL,
        "tenant-b",
    )

    task = queue.dequeue()

    assert task["tenant_id"] == "tenant-b"
    assert task["priority"] == "CRITICAL"


def test_priority_and_fairness_together():
    redis = fakeredis.FakeRedis(decode_responses=True)
    queue = PriorityTaskQueue(redis)

    # Tenant A has a LOW task.
    queue.enqueue(
        {"message": "A-low"},
        TaskPriority.LOW,
        "tenant-a",
    )

    # Tenant B has a CRITICAL task.
    queue.enqueue(
        {"message": "B-critical"},
        TaskPriority.CRITICAL,
        "tenant-b",
    )

    # Tenant C has a CRITICAL task.
    queue.enqueue(
        {"message": "C-critical"},
        TaskPriority.CRITICAL,
        "tenant-c",
    )

    first = queue.dequeue()
    second = queue.dequeue()
    third = queue.dequeue()

    assert first["priority"] == "CRITICAL"
    assert second["priority"] == "CRITICAL"

    assert {
        first["tenant_id"],
        second["tenant_id"],
    } == {
        "tenant-b",
        "tenant-c",
    }

    assert third["tenant_id"] == "tenant-a"
    assert third["priority"] == "LOW"


def test_celery_consumer_executes_runtime_task():
    import app.services.task_queue_worker
    from app.tasks import consume_task_queue

    redis = fakeredis.FakeRedis(decode_responses=True)
    queue = PriorityTaskQueue(redis)

    queue.enqueue(
        {
            "task_type": "dispatch",
            "context": {
                "job_id": "job-123",
                "message": "test task",
            },
        },
        TaskPriority.NORMAL,
        "tenant-a",
    )

    original_get_redis_client = (
        app.services.task_queue_worker.get_redis_client
    )
    original_orchestrator = (
        app.services.task_queue_worker.ai_orchestrator
    )

    class FakeRuntime:
        def execute(self, task, context):
            assert task.value == "dispatch"
            assert context["job_id"] == "job-123"

            return {
                "status": "executed",
                "job_id": context["job_id"],
            }

    try:
        app.services.task_queue_worker.get_redis_client = (
            lambda: redis
        )

        app.services.task_queue_worker.ai_orchestrator = (
            FakeRuntime()
        )

        result = consume_task_queue.apply(args=()).get()

        assert result is not None
        assert result["success"] is True
        assert result["result"]["status"] == "executed"
        assert result["result"]["job_id"] == "job-123"
        assert queue.depth("tenant-a") == 0

    finally:
        app.services.task_queue_worker.get_redis_client = (
            original_get_redis_client
        )
        app.services.task_queue_worker.ai_orchestrator = (
            original_orchestrator
        )