from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.retention import (
    RetentionCRMTask,
    RetentionDiscountCode,
    RetentionServiceCredit,
    RetentionWorkflow,
)
from app.sentiment.retention import RetentionWorkflowService


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            RetentionWorkflow.__table__,
            RetentionDiscountCode.__table__,
            RetentionCRMTask.__table__,
            RetentionServiceCredit.__table__,
        ],
    )
    return sessionmaker(bind=engine)()


def test_negative_sentiment_triggers_workflow():
    db = make_db()
    workflow = RetentionWorkflowService(db).create_workflow(
        tenant_id="tenant-1", customer_id="customer-1", sentiment="NEGATIVE",
        confidence=0.71, message="This service is frustrating",
    )
    assert workflow is not None
    assert workflow.trigger_type == "negative_sentiment"


def test_churn_keyword_triggers_without_negative_label():
    db = make_db()
    workflow = RetentionWorkflowService(db).create_workflow(
        tenant_id="tenant-1", customer_id="customer-1", sentiment="NEUTRAL",
        confidence=0.2, message="I am switching to competitor today",
    )
    assert workflow is not None
    assert workflow.trigger_type == "churn_keyword"


def test_non_trigger_is_ignored():
    assert RetentionWorkflowService.detect_trigger("NEGATIVE", 0.7, "Not ideal") is None


def test_execute_creates_all_five_actions_and_discount_invariants():
    db = make_db()
    workflow = RetentionWorkflowService(db).create_workflow(
        tenant_id="tenant-1", customer_id="customer-1", sentiment="NEGATIVE",
        confidence=0.95, message="Cancel subscription", customer_lifetime_value=1500,
    )
    result = RetentionWorkflowService(db).execute(workflow)
    discount = db.get(RetentionDiscountCode, result["discount_code"])
    assert result["actions"] == ["apology_message", "discount", "follow_up_call", "service_credit", "specialist_assignment"]
    assert discount.percentage == 20
    assert discount.usage_limit == 1
    expires_at = discount.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    assert timedelta(days=6, hours=23) < expires_at - datetime.now(timezone.utc) <= timedelta(days=7)
    assert db.query(RetentionCRMTask).count() == 1
    assert db.query(RetentionServiceCredit).one().applied is True
    assert result["specialist"] == "retention-specialist"


def test_branching_selects_standard_recovery_for_lower_value_customer():
    db = make_db()
    workflow = RetentionWorkflowService(db).create_workflow(
        tenant_id="tenant-1", customer_id="customer-1", sentiment="NEGATIVE",
        confidence=0.82, message="Bad experience", customer_lifetime_value=999,
    )
    assert workflow.severity == "high"
    assert workflow.branch == "standard_recovery"


def test_success_tracking_counts_retained_rate():
    db = make_db()
    service = RetentionWorkflowService(db)
    retained = service.create_workflow(tenant_id="tenant-1", customer_id="one", sentiment="NEGATIVE", confidence=0.8)
    churned = service.create_workflow(tenant_id="tenant-1", customer_id="two", message="never using again")
    service.track_outcome(retained.id, True)
    service.track_outcome(churned.id, False)
    assert retained.outcome == "retained"
    assert churned.outcome == "churned"
    assert service.success_rate("tenant-1") == 0.5
