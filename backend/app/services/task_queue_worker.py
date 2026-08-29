from typing import Any

from app.celery_app import celery_app
from app.redis_client import get_redis_client
from app.services.task_queue import PriorityTaskQueue
from app.services.ai.FieldOpsAI.runtime.orchestrator import (
    ai_orchestrator,
)
from app.services.ai.FieldOpsAI.schemas.ai_task import AITask


@celery_app.task(
    name="app.tasks.consume_task_queue"
)
def consume_task_queue() -> dict[str, Any] | None:
    """
    Consume one task from the priority queue and execute it
    through the existing FieldOps AI Runtime.
    """

    redis = get_redis_client()

    if redis is None:
        return None

    queue = PriorityTaskQueue(redis)

    task = queue.dequeue()

    if task is None:
        return None

    payload = task.get("payload", {})

    task_type = payload.get("task_type")

    if not task_type:
        return {
            "task_id": task["task_id"],
            "success": False,
            "error": "Task type is required",
        }

    try:
        ai_task = AITask(task_type)
    except ValueError:
        return {
            "task_id": task["task_id"],
            "success": False,
            "error": f"Unsupported task type: {task_type}",
        }

    context = payload.get("context", {})

    try:
        result = ai_orchestrator.execute(
            ai_task,
            context,
        )

        return {
            "task_id": task["task_id"],
            "success": True,
            "result": result,
        }

    except Exception as exc:
        return {
            "task_id": task["task_id"],
            "success": False,
            "error": str(exc),
        }