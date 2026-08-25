from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.retention import RetentionWorkflow
from app.sentiment.retention import RetentionWorkflowService

router = APIRouter(prefix="/admin/retention", tags=["Retention"])


class RetentionTriggerRequest(BaseModel):
    tenant_id: str
    customer_id: str
    sentiment: str | None = None
    confidence: float | None = Field(None, ge=0, le=1)
    message: str | None = None
    customer_lifetime_value: float = Field(0, ge=0)


class RetentionOutcomeRequest(BaseModel):
    retained: bool


def _serialize(workflow: RetentionWorkflow) -> dict[str, Any]:
    return {"id": workflow.id, "tenant_id": workflow.tenant_id, "customer_id": workflow.customer_id,
            "trigger_type": workflow.trigger_type, "severity": workflow.severity, "branch": workflow.branch,
            "status": workflow.status, "actions": workflow.actions, "outcome": workflow.outcome,
            "customer_lifetime_value": workflow.customer_lifetime_value,
            "created_at": workflow.created_at.isoformat() if workflow.created_at else None}


@router.get("/workflows")
def list_retention_workflows(tenant_id: str | None = None, db: Session = Depends(get_db)):
    query = db.query(RetentionWorkflow)
    if tenant_id:
        query = query.filter(RetentionWorkflow.tenant_id == tenant_id)
    return [_serialize(item) for item in query.order_by(RetentionWorkflow.created_at.desc()).all()]


@router.post("/workflows")
def create_retention_workflow(payload: RetentionTriggerRequest, db: Session = Depends(get_db)):
    workflow = RetentionWorkflowService(db).create_workflow(**payload.model_dump())
    if workflow is None:
        raise HTTPException(status_code=422, detail="Retention trigger conditions were not met")
    return _serialize(workflow)


@router.post("/workflows/{workflow_id}/execute")
def execute_retention_workflow(workflow_id: str, db: Session = Depends(get_db)):
    workflow = db.get(RetentionWorkflow, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Retention workflow not found")
    return RetentionWorkflowService(db).execute(workflow)


@router.post("/workflows/{workflow_id}/outcome")
def track_retention_outcome(workflow_id: str, payload: RetentionOutcomeRequest, db: Session = Depends(get_db)):
    try:
        workflow = RetentionWorkflowService(db).track_outcome(workflow_id, payload.retained)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"workflow": _serialize(workflow), "success_rate": RetentionWorkflowService(db).success_rate(workflow.tenant_id)}