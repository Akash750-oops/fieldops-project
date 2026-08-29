from fastapi import APIRouter, Depends

from app.services.task_queue import PriorityTaskQueue
from app.redis_client import get_redis_client


router = APIRouter(
    prefix="/admin/queue",
    tags=["Admin Queue"],
)


def get_task_queue() -> PriorityTaskQueue:
    redis = get_redis_client()
    return PriorityTaskQueue(redis)


@router.get("/stats")
def get_queue_stats(
    queue: PriorityTaskQueue = Depends(get_task_queue),
):
    return queue.stats()