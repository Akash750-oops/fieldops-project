from fastapi import APIRouter, Depends

from app.services.task_queue import PriorityTaskQueue
from app.redis_client import get_redis_client

from app.auth.dependencies import (
    AuthenticatedUser,
    get_current_user,
    require_permission,
)
from app.auth.rbac import Permission


router = APIRouter(
    prefix="/admin/queue",
    tags=["Admin Queue"],
)


def get_task_queue() -> PriorityTaskQueue:
    redis = get_redis_client()
    return PriorityTaskQueue(redis)


@router.get(
    "/stats",
    dependencies=[
        Depends(
            require_permission(
                Permission.DISPATCH_QUEUE_VIEW
            )
        )
    ],
)
def get_queue_stats(
    queue: PriorityTaskQueue = Depends(get_task_queue),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Return queue statistics for the authenticated user's tenant.
    """

    return queue.stats(
        tenant_id=current_user.tenant_id
    )