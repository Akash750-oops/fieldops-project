"""
Dead Letter Queue management.

Provides Redis-backed operational storage and PostgreSQL-backed
persistent archival for permanently failed tasks.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.dead_letter_task import DeadLetterTask


class DeadLetterQueue:
    """
    Manage permanently failed tasks.

    Redis:
        Operational DLQ used for fast inspection/recovery.

    PostgreSQL:
        Durable archive used for persistence, auditing, and
        administrative operations.

    The same DLQ ID is stored in both systems.
    """

    DLQ_KEY = "task_queue:dlq"

    def __init__(
        self,
        redis_client,
        db: Session | None = None,
    ):
        self.redis = redis_client
        self.db = db

    def add(
        self,
        task: dict[str, Any],
        reason: str,
        retry_count: int = 0,
        error: BaseException | None = None,
        celery_task_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Add a failed task to Redis and PostgreSQL.
        """

        error_type = None
        error_message = None

        if error is not None:
            error_type = error.__class__.__name__
            error_message = str(error)

        payload = task.get("payload", {})

        context = (
            payload.get("context", {})
            if isinstance(payload, dict)
            else {}
        )

        task_type = (
            payload.get("task_type")
            if isinstance(payload, dict)
            else None
        )

        tenant_id = task.get("tenant_id")

        if not tenant_id:
            raise ValueError(
                "tenant_id is required for DLQ persistence"
            )

        dlq_id = str(uuid.uuid4())

        entry = {
            "id": dlq_id,
            "task": task,
            "reason": reason,
            "retry_count": retry_count,
            "error_type": error_type,
            "error_message": error_message,
            "status": "FAILED",
            "moved_at": time.time(),
        }

        # Redis operational DLQ.
        self.redis.rpush(
            self.DLQ_KEY,
            json.dumps(entry),
        )

        # PostgreSQL permanent archive.
        if self.db is not None:
            database_entry = DeadLetterTask(
                id=dlq_id,
                task_id=task["task_id"],
                celery_task_id=celery_task_id,
                task_type=task_type,
                tenant_id=tenant_id,
                payload=payload,
                context=context,
                reason=reason,
                error_type=error_type,
                error_message=error_message,
                retry_count=retry_count,
                status="FAILED",
            )

            self.db.add(database_entry)
            self.db.flush()

        return entry

    def count(self) -> int:
        """Return current Redis DLQ item count."""

        return int(
            self.redis.llen(self.DLQ_KEY)
        )

    def list(
        self,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Return Redis DLQ items in insertion order.
        """

        if limit is not None:
            if limit <= 0:
                return []

            end = limit - 1
        else:
            end = -1

        raw_items = self.redis.lrange(
            self.DLQ_KEY,
            0,
            end,
        )

        result = []

        for item in raw_items:
            if isinstance(item, bytes):
                item = item.decode("utf-8")

            result.append(
                json.loads(item)
            )

        return result

    def get(
        self,
        dlq_id: str,
    ) -> dict[str, Any] | None:
        """Find a Redis DLQ item by identifier."""

        for item in self.list():
            if item.get("id") == dlq_id:
                return item

        return None

    def delete(
        self,
        dlq_id: str,
    ) -> bool:
        """
        Remove a DLQ item from Redis.

        PostgreSQL remains the permanent archive.
        """

        items = self.list()

        matching_items = [
            item
            for item in items
            if item.get("id") == dlq_id
        ]

        if not matching_items:
            return False

        remaining_items = [
            item
            for item in items
            if item.get("id") != dlq_id
        ]

        pipeline = self.redis.pipeline()

        pipeline.delete(self.DLQ_KEY)

        if remaining_items:
            pipeline.rpush(
                self.DLQ_KEY,
                *[
                    json.dumps(item)
                    for item in remaining_items
                ],
            )

        pipeline.execute()

        return True

    def requeue_payload(
        self,
        dlq_id: str,
    ) -> dict[str, Any] | None:
        """
        Return original task for manual requeueing.
        """

        item = self.get(dlq_id)

        if item is None:
            return None

        return item.get("task")

    def get_failed_items(
        self,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Return failed DLQ items eligible for auto-requeue.
        """

        if limit <= 0:
            return []

        items = self.list(
            limit=limit
        )

        return [
            item
            for item in items
            if item.get("status", "FAILED") == "FAILED"
        ]

    def auto_requeue(
        self,
        queue,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Automatically requeue failed DLQ tasks.

        A task is removed from the DLQ only after successful
        insertion into the priority task queue.
        """

        if limit <= 0:
            return []

        from app.services.task_queue import TaskPriority

        failed_items = self.get_failed_items(
            limit=limit
        )

        requeued: list[dict[str, Any]] = []

        for item in failed_items:
            task = item.get("task")

            if not isinstance(task, dict):
                continue

            tenant_id = task.get("tenant_id")

            if not tenant_id:
                continue

            payload = task.get("payload", {})

            priority_name = (
                payload.get(
                    "priority",
                    "NORMAL",
                )
                if isinstance(payload, dict)
                else "NORMAL"
            )

            try:
                priority = TaskPriority[
                    str(priority_name).upper()
                ]
            except (KeyError, TypeError):
                priority = TaskPriority.NORMAL

            try:
                new_task_id = queue.enqueue(
                    task=payload,
                    priority=priority,
                    tenant_id=tenant_id,
                )
            except Exception:
                # Keep the DLQ item if requeue fails.
                continue

            dlq_id = item.get("id")

            if not dlq_id:
                continue

            deleted = self.delete(dlq_id)

            if not deleted:
                continue

            requeued.append(
                {
                    "dlq_id": dlq_id,
                    "old_task_id": task.get("task_id"),
                    "new_task_id": new_task_id,
                    "tenant_id": tenant_id,
                }
            )

        return requeued

    def is_above_alert_threshold(
        self,
        threshold: int = 10,
    ) -> bool:
        """
        Return True when DLQ count exceeds threshold.
        """

        return self.count() > threshold