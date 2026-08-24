from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.database import Base
from app.prompts.analytics import PromptAnalytics


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def make_prompt(db, *, tenant_id="tenant-1", agent_type="CommsAgent", channel="sms"):
    organization = models.Organization(
        id=tenant_id,
        name=f"Org {tenant_id}",
        slug=tenant_id,
    )
    db.add(organization)
    db.flush()
    prompt = models.NotificationTemplate(
        name="Analytics prompt",
        type="job_created",
        channel=channel,
        locale="en",
        format="text",
        body_template="Hello",
        variables=[],
        tenant_id=tenant_id,
        agent_type=agent_type,
    )
    db.add(prompt)
    db.commit()
    return prompt


def test_metrics_period_quality_and_redis_counter():
    db = make_session()
    prompt = make_prompt(db)
    redis = {}

    class Redis:
        def incr(self, key):
            redis[key] = redis.get(key, 0) + 1

    analytics = PromptAnalytics(db, Redis(), "tenant-1")
    now = datetime.now(timezone.utc)
    analytics.record_usage(prompt.id, 100, 10, False, False, engaged=True, occurred_at=now)
    analytics.record_usage(prompt.id, 300, 30, True, False, engaged=False, occurred_at=now - timedelta(days=2))
    analytics.record_usage(prompt.id, 500, 50, False, True, engaged=True, occurred_at=now - timedelta(days=10))

    recent = analytics.get_prompt_metrics(prompt.id, 7)
    assert recent.usage_count == 2
    assert recent.avg_latency_ms == 200
    assert recent.avg_tokens == 20
    assert recent.fallback_rate == 0.5
    assert recent.error_rate == 0
    assert recent.quality_score == 57.5
    assert redis[f"prompt_analytics:tenant-1:prompt:{prompt.id}:usage"] == 3

    trends = analytics.get_trends(prompt.id)
    assert trends["7"].usage_count == 2
    assert trends["30"].usage_count == 3


def test_dashboard_is_preaggregated_for_all_dimensions():
    db = make_session()
    prompt = make_prompt(db, agent_type="SentimentAgent", channel="email")
    analytics = PromptAnalytics(db, tenant_id="tenant-1")
    analytics.record_usage(prompt.id, 100, 10, False, False, occurred_at=datetime.now(timezone.utc))

    assert analytics.aggregate_dashboard() == 6
    dashboard = analytics.dashboard(7)
    assert {(row["dimension"], row["key"]) for row in dashboard} == {
        ("agent", "SentimentAgent"),
        ("channel", "email"),
        ("prompt", str(prompt.id)),
    }


def test_engagement_is_recorded_and_tenant_scoped():
    db = make_session()
    prompt = make_prompt(db)
    event = PromptAnalytics(db, tenant_id="tenant-1").record_usage(
        prompt.id, 100, 10, False, False, engaged=None,
    )

    updated = PromptAnalytics(db, tenant_id="tenant-1").record_engagement(
        event.id, True,
    )
    assert updated.engaged is True
    assert PromptAnalytics(db, tenant_id="tenant-1").get_prompt_metrics(
        prompt.id,
    ).engagement_rate == 1.0

    try:
        PromptAnalytics(db, tenant_id="other-tenant").record_engagement(
            event.id, False,
        )
    except ValueError as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("Cross-tenant engagement update was accepted")