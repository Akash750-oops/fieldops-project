from enum import IntEnum
from typing import Any, Optional
import json
import time
import uuid
class QueueBackpressureError(Exception):
    """Raised when queue ingestion is paused because the queue is too deep."""

class TaskPriority(IntEnum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


class PriorityTaskQueue:
    """
    Redis-backed priority task queue.

    Queue structure:
        task_queue:tenant:{tenant_id}
        task_queue:global

    Lower priority number means higher priority.
    """
   
    TENANT_QUEUE_PREFIX = "task_queue:tenant:"
    GLOBAL_QUEUE = "task_queue:global"

    TENANT_REGISTRY = "task_queue:tenants"
    ROUND_ROBIN_TENANT = "task_queue:round_robin_tenant"
    DLQ_KEY = "task_queue:dlq"
    BACKPRESSURE_THRESHOLD = 10_000
    THROUGHPUT_KEY = "task_queue:throughput"
 
    def __init__(self, redis_client):
        self.redis = redis_client

    def _queue_key(self, tenant_id: Optional[str]) -> str:
        if tenant_id:
            return f"{self.TENANT_QUEUE_PREFIX}{tenant_id}"

        return self.GLOBAL_QUEUE

    def enqueue(
        self,
        task: dict[str, Any],
        priority: TaskPriority,
        tenant_id: Optional[str] = None,
    ) -> str:
        """
        Add a task to the appropriate Redis sorted set.

        Returns:
            task_id
        """

        if not isinstance(priority, TaskPriority):
            priority = TaskPriority(priority)

        task_id = str(uuid.uuid4())

        payload = {
            "task_id": task_id,
            "tenant_id": tenant_id,
            "priority": priority.name,
            "created_at": time.time(),
            "payload": task,
        }

        if self.is_backpressured():
            raise QueueBackpressureError(
                "Task queue ingestion paused: queue depth exceeds 10,000"
            )

        queue_key = self._queue_key(tenant_id)

        if tenant_id:
            self.redis.sadd(
                self.TENANT_REGISTRY,
                tenant_id,
            )

        # Priority comes first, creation time is used as tie breaker.
        score = (priority.value * 1_000_000_000_000) + time.time()

        self.redis.zadd(
            queue_key,
            {
                json.dumps(payload): score
            }
        )

        return task_id

    def depth(self, tenant_id: Optional[str] = None) -> int:
        """
        Return number of tasks currently waiting in a queue.
        """

        queue_key = self._queue_key(tenant_id)

        return self.redis.zcard(queue_key)

    def peek(
        self,
        tenant_id: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """
        Look at the highest-priority task without removing it.
        """

        queue_key = self._queue_key(tenant_id)

        result = self.redis.zrange(
            queue_key,
            0,
            0,
        )

        if not result:
            return None

        return json.loads(result[0])

    def dequeue(self) -> Optional[dict[str, Any]]:
        """
        Dequeue one task using priority first and round-robin fairness
        between tenants with the same highest priority.

        Priority:
            CRITICAL > HIGH > NORMAL > LOW

        Fairness:
            Tenants sharing the same priority get round-robin turns.
        """

        tenants = sorted(
            self.redis.smembers(self.TENANT_REGISTRY)
        )

        if not tenants:
            return None

        candidates = []

        for tenant_id in tenants:
            queue_key = self._queue_key(tenant_id)

            result = self.redis.zrange(
                queue_key,
                0,
                0,
            )

            if not result:
                continue

            raw_task = result[0]
            task = json.loads(raw_task)

            candidates.append(
                {
                    "tenant_id": tenant_id,
                    "raw_task": raw_task,
                    "task": task,
                }
            )

        if not candidates:
            return None

        # Find the highest priority currently available.
        highest_priority = min(
            candidate["task"]["priority"]
            for candidate in candidates
        )

        priority_candidates = [
            candidate
            for candidate in candidates
            if candidate["task"]["priority"] == highest_priority
        ]

        # Apply round-robin only between tenants that have
        # the same highest priority.
        last_tenant = self.redis.get(
            self.ROUND_ROBIN_TENANT
        )

        priority_tenants = [
            candidate["tenant_id"]
            for candidate in priority_candidates
        ]

        if last_tenant in priority_tenants:
            last_index = priority_tenants.index(last_tenant)
            selected_index = (
                last_index + 1
            ) % len(priority_tenants)
        else:
            # The previous tenant may have become empty and
            # been removed from the registry. Continue with the
            # next surviving tenant.
            selected_index = 0

            if last_tenant is not None:
                for index, tenant_id in enumerate(priority_tenants):
                    if tenant_id > last_tenant:
                        selected_index = index
                        break

        selected = priority_candidates[selected_index]

        tenant_id = selected["tenant_id"]
        raw_task = selected["raw_task"]

        queue_key = self._queue_key(tenant_id)

        removed = self.redis.zrem(
            queue_key,
            raw_task,
        )

        if not removed:
            return None

        self.redis.incr(self.THROUGHPUT_KEY)

        self.redis.set(
            self.ROUND_ROBIN_TENANT,
            tenant_id,
        )

        if self.redis.zcard(queue_key) == 0:
            self.redis.srem(
                self.TENANT_REGISTRY,
                tenant_id,
            )

        return selected["task"]

    def move_to_dlq(self, task: dict[str, Any], reason: str) -> None:
        """
        Move a failed task to the dead letter queue.

        Retry decisions are handled by Task 3.6.
        """

        dlq_entry = {
            "task": task,
            "reason": reason,
            "moved_at": time.time(),
        }

        self.redis.rpush(
            self.DLQ_KEY,
            json.dumps(dlq_entry),
        )

    def is_backpressured(
        self,
        tenant_id: Optional[str] = None,
    ) -> bool:
        """ 
        Return True when total queue depth is above
        the backpressure threshold.
        """

        return self.total_depth() > self.BACKPRESSURE_THRESHOLD

    def oldest_task_age(
        self,
        tenant_id: Optional[str] = None,
    ) -> float:
        """
        Return the age in seconds of the oldest queued task.
        """

        task = self.peek(tenant_id)

        if task is None:
            return 0.0

        return max(
            0.0,
            time.time() - task["created_at"],
        )


    def throughput(
        self,
        tenant_id: Optional[str] = None,
    ) -> int:
        """
        Return the number of successfully dequeued tasks.
        """

        return int(
            self.redis.get(self.THROUGHPUT_KEY) or 0
        )


    def stats(
        self,
        tenant_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Return current queue statistics.
        """

        return {
            "depth": self.depth(tenant_id),
            "oldest_task_age": self.oldest_task_age(tenant_id),
            "throughput": self.throughput(tenant_id),
        }

    def total_depth(self) -> int:
        """
        Return the total number of queued tasks across all
        tenant queues and the global queue.
        """

        total = self.redis.zcard(self.GLOBAL_QUEUE)

        tenant_queue_pattern = (
            f"{self.TENANT_QUEUE_PREFIX}*"
        )

        for queue_key in self.redis.scan_iter(
            match=tenant_queue_pattern
        ):
            total += self.redis.zcard(queue_key)

        return total

    