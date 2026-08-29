from fastapi import APIRouter

from app.runtime.metrics import MetricsCollector

router = APIRouter(prefix="/admin/metrics", tags=["Admin Metrics"])
collector = MetricsCollector()


@router.get("")
def get_metrics() -> dict:
    return collector.snapshot()


@router.get("/agents")
def get_agent_metrics() -> dict:
    return collector.agent_snapshot()


@router.get("/tenants")
def get_tenant_metrics() -> dict:
    return collector.tenant_snapshot()
