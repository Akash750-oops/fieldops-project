from __future__ import annotations

from typing import Any

from app.database import SessionLocal
from app.celery_app import celery_app
from app.redis_client import get_redis_client
from app.runtime.dlq import DeadLetterQueue
from app.runtime.retry import RetryDecision, RetryManager
from app.services.enterprise_audit import AuditAction, audit_log
from app.services.task_queue import PriorityTaskQueue
from app.services.ai.FieldOpsAI.runtime.orchestrator import (
    ai_orchestrator,
)
from app.services.ai.FieldOpsAI.schemas.ai_task import AITask


@celery_app.task(
    bind=True,
    name="app.tasks.consume_task_queue",
    max_retries=3,
)
def consume_task_queue(
    self,
    task: dict[str, Any] | None = None,
    retry_count: int = 0,
) -> dict[str, Any] | None:
    """
    Consume and execute one task from the priority queue.

    Initial execution:
        task=None
        -> dequeue one task from PriorityTaskQueue

    Retry execution:
        task=<original task>
        -> execute the same task again

    Retry policy:
        Retry 1 -> 1 second
        Retry 2 -> 2 seconds
        Retry 3 -> 4 seconds

    After the final retry fails, the task is persisted
    to the Redis + PostgreSQL DLQ.
    """

    redis = get_redis_client()

    if redis is None:
        return None

    queue = PriorityTaskQueue(redis)

    # Initial execution dequeues exactly once.
    # Retry executions reuse the original task.
    if task is None:
        task = queue.dequeue()

    if task is None:
        return None

    task_id = task["task_id"]

    payload = task.get("payload", {})
    task_type = payload.get("task_type")

    # ----------------------------------------------------------
    # Permanent failure: missing task type
    # ----------------------------------------------------------

    if not task_type:
        return _move_task_to_dlq(
            redis=redis,
            task=task,
            reason="task_type_required",
            retry_count=retry_count,
            error=ValueError("Task type is required"),
            celery_task_id=self.request.id,
        )

    # ----------------------------------------------------------
    # Permanent failure: unsupported task type
    # ----------------------------------------------------------

    try:
        ai_task = AITask(task_type)
    except ValueError as exc:
        return _move_task_to_dlq(
            redis=redis,
            task=task,
            reason="unsupported_task_type",
            retry_count=retry_count,
            error=exc,
            celery_task_id=self.request.id,
        )

    context = payload.get("context", {})

    # ----------------------------------------------------------
    # Execute task
    # ----------------------------------------------------------

    try:
        result = ai_orchestrator.execute(
            ai_task,
            context,
        )

        return {
            "task_id": task_id,
            "success": True,
            "result": result,
            "retry_count": retry_count,
        }

    except Exception as exc:
        retry_result = RetryManager.evaluate(
            error=exc,
            retry_count=retry_count,
        )

        # ------------------------------------------------------
        # Retryable failure
        # ------------------------------------------------------

        if retry_result.decision == RetryDecision.RETRY:
            next_retry_count = retry_result.retry_number

            db = SessionLocal()

            try:
                audit_log(
                    db,
                    action=AuditAction.TASK_RETRY,
                    tenant_id=task["tenant_id"],
                    entity_type="task",
                    entity_id=task_id,
                    details={
                        "retry_number": next_retry_count,
                        "retry_delay_seconds": retry_result.delay_seconds,
                        "reason": retry_result.reason,
                        "error_type": exc.__class__.__name__,
                        "error_message": str(exc),
                        "celery_task_id": self.request.id,
                    },
                    severity="WARNING",
                )

                # Audit must be committed before Celery retry.
                db.commit()

            except Exception:
                db.rollback()
                raise

            finally:
                db.close()

            # Important:
            # Re-submit the SAME task payload.
            # Do not dequeue another task.
            raise self.retry(
                args=[task],
                kwargs={
                    "retry_count": next_retry_count,
                },
                countdown=retry_result.delay_seconds,
                exc=exc,
            )

        # ------------------------------------------------------
        # Permanent failure -> DLQ
        # ------------------------------------------------------

        return _move_task_to_dlq(
            redis=redis,
            task=task,
            reason=retry_result.reason,
            retry_count=retry_count,
            error=exc,
            celery_task_id=self.request.id,
        )


def _move_task_to_dlq(
    redis,
    task: dict[str, Any],
    reason: str,
    retry_count: int,
    error: BaseException,
    celery_task_id: str | None = None,
) -> dict[str, Any]:
    """
    Persist a permanently failed task to Redis + PostgreSQL
    and create an audit record.

    PostgreSQL transaction is committed only after both the
    DLQ record and audit record have been created.
    """

    db = SessionLocal()

    try:
        dlq = DeadLetterQueue(
            redis_client=redis,
            db=db,
        )

        entry = dlq.add(
            task=task,
            reason=reason,
            retry_count=retry_count,
            error=error,
            celery_task_id=celery_task_id,
        )

        audit_log(
            db,
            action=AuditAction.TASK_DLQ,
            tenant_id=task["tenant_id"],
            entity_type="task",
            entity_id=task["task_id"],
            details={
                "dlq_id": entry["id"],
                "reason": reason,
                "retry_count": retry_count,
                "error_type": error.__class__.__name__,
                "error_message": str(error),
                "celery_task_id": celery_task_id,
            },
            severity="ERROR",
        )

        db.commit()

        return {
            "task_id": task["task_id"],
            "success": False,
            "error": str(error),
            "retry_count": retry_count,
            "retry_decision": RetryDecision.DLQ.value,
            "retry_reason": reason,
            "dlq_id": entry["id"],
        }

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


# ------------------------------------------------------------------
# Test/runtime compatibility
# ------------------------------------------------------------------
#
# Some existing tests access the task using:
#
#     consume_task_queue._get_current_object()
#
# Celery's Task object does not normally expose that Flask-style
# helper. Expose it as a compatibility shim while keeping the real
# Celery task object unchanged.
#
# This returns the registered Celery task itself.
#

if not hasattr(consume_task_queue, "_get_current_object"):
    consume_task_queue._get_current_object = lambda: consume_task_queue