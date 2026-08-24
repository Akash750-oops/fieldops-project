from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, func
from sqlalchemy.orm import Session

from app import models


@dataclass(frozen=True)
class Metrics:
    usage_count: int = 0
    avg_latency_ms: float = 0.0
    avg_tokens: float = 0.0
    fallback_rate: float = 0.0
    error_rate: float = 0.0
    engagement_rate: float = 0.0
    quality_score: float = 0.0
    period_days: int = 7

    @property
    def avg_latency(self) -> float:
        return self.avg_latency_ms

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PromptAnalytics:
    """Record prompt executions and calculate tenant-scoped performance metrics."""

    def __init__(self, db: Session, redis_client: Any | None = None, tenant_id: str | None = None):
        self.db = db
        self.redis = redis_client
        self.tenant_id = tenant_id

    def record_usage(
        self,
        prompt_id: int,
        latency: float,
        tokens: int,
        fallback: bool,
        error: bool,
        *,
        agent_type: str | None = None,
        channel: str | None = None,
        engaged: bool | None = None,
        occurred_at: datetime | None = None,
    ) -> models.PromptUsageEvent:
        prompt = self.db.get(models.NotificationTemplate, prompt_id)
        if prompt is None:
            raise ValueError(f"Prompt {prompt_id} was not found")
        if self.tenant_id is not None and prompt.tenant_id != self.tenant_id:
            raise ValueError("Prompt does not belong to the analytics tenant")

        event = models.PromptUsageEvent(
            id=str(uuid4()),
            prompt_id=prompt_id,
            tenant_id=self.tenant_id or prompt.tenant_id,
            agent_type=agent_type or prompt.agent_type,
            channel=channel or prompt.channel,
            latency_ms=max(float(latency), 0.0),
            tokens=max(int(tokens), 0),
            fallback=bool(fallback),
            error=bool(error),
            engaged=engaged,
            occurred_at=occurred_at or datetime.now(timezone.utc),
        )
        self.db.add(event)
        self.db.commit()
        self._increment_realtime(event)
        return event

    def get_prompt_metrics(self, prompt_id: int, period: int | str = 7) -> Metrics:
        query = self._base_query(period).filter(models.PromptUsageEvent.prompt_id == prompt_id)
        return self._metrics(query, period)

    def get_agent_metrics(self, agent_type: str, period: int | str = 7) -> Metrics:
        query = self._base_query(period).filter(models.PromptUsageEvent.agent_type == agent_type)
        return self._metrics(query, period)

    def get_channel_metrics(self, channel: str, period: int | str = 7) -> Metrics:
        query = self._base_query(period).filter(models.PromptUsageEvent.channel == channel)
        return self._metrics(query, period)

    def record_engagement(self, event_id: str, engaged: bool) -> models.PromptUsageEvent:
        """Attach a customer engagement outcome to an existing usage event."""
        query = self.db.query(models.PromptUsageEvent).filter(
            models.PromptUsageEvent.id == event_id,
        )
        if self.tenant_id is not None:
            query = query.filter(models.PromptUsageEvent.tenant_id == self.tenant_id)
        event = query.one_or_none()
        if event is None:
            raise ValueError(f"Usage event {event_id} was not found")
        event.engaged = bool(engaged)
        self.db.commit()
        return event

    def get_trends(
        self,
        prompt_id: int | None = None,
        agent_type: str | None = None,
        channel: str | None = None,
    ) -> dict[str, Metrics]:
        query = self._base_query(30)
        if prompt_id is not None:
            query = query.filter(models.PromptUsageEvent.prompt_id == prompt_id)
        if agent_type is not None:
            query = query.filter(models.PromptUsageEvent.agent_type == agent_type)
        if channel is not None:
            query = query.filter(models.PromptUsageEvent.channel == channel)
        return {str(days): self._metrics(query, days) for days in (7, 30)}

    def aggregate_dashboard(self, at: datetime | None = None) -> int:
        """Materialize prompt, agent, and channel metrics for both rolling windows."""
        calculated_at = at or datetime.now(timezone.utc)
        dimensions = (
            ("prompt", models.PromptUsageEvent.prompt_id),
            ("agent", models.PromptUsageEvent.agent_type),
            ("channel", models.PromptUsageEvent.channel),
        )
        written = 0
        for dimension, column in dimensions:
            keys = self._base_query(30, calculated_at).with_entities(column).distinct().all()
            for (key,) in keys:
                for days in (7, 30):
                    query = self._base_query(days, calculated_at).filter(column == key)
                    metrics = self._metrics(query, days, calculated_at)
                    self._store_aggregate(
                        dimension=dimension,
                        dimension_key=str(key),
                        period_days=days,
                        metrics=metrics.to_dict(),
                        calculated_at=calculated_at,
                    )
                    written += 1
        self.db.commit()
        return written

    def _store_aggregate(
        self,
        *,
        dimension: str,
        dimension_key: str,
        period_days: int,
        metrics: dict[str, Any],
        calculated_at: datetime,
    ) -> None:
        values = {
            "tenant_id": self.tenant_id,
            "dimension": dimension,
            "dimension_key": dimension_key,
            "period_days": period_days,
            "metrics": metrics,
            "calculated_at": calculated_at,
        }
        bind = self.db.get_bind()
        if bind.dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import insert

            statement = insert(models.PromptAnalyticsAggregate).values(
                id=str(uuid4()), **values
            ).on_conflict_do_update(
                index_elements=[
                    "tenant_id", "dimension", "dimension_key", "period_days"
                ],
                set_={"metrics": metrics, "calculated_at": calculated_at},
            )
            self.db.execute(statement)
            return

        aggregate = self.db.query(models.PromptAnalyticsAggregate).filter_by(
            tenant_id=self.tenant_id,
            dimension=dimension,
            dimension_key=dimension_key,
            period_days=period_days,
        ).one_or_none()
        if aggregate is None:
            self.db.add(models.PromptAnalyticsAggregate(id=str(uuid4()), **values))
        else:
            aggregate.metrics = metrics
            aggregate.calculated_at = calculated_at

    def dashboard(self, period: int | str = 7) -> list[dict[str, Any]]:
        rows = self.db.query(models.PromptAnalyticsAggregate).filter_by(
            tenant_id=self.tenant_id,
            period_days=self._period(period),
        ).order_by(
            models.PromptAnalyticsAggregate.dimension,
            models.PromptAnalyticsAggregate.dimension_key,
        ).all()
        return [
            {"dimension": row.dimension, "key": row.dimension_key, "metrics": row.metrics}
            for row in rows
        ]

    def _base_query(self, period: int | str, as_of: datetime | None = None):
        cutoff = (as_of or datetime.now(timezone.utc)) - timedelta(days=self._period(period))
        query = self.db.query(models.PromptUsageEvent).filter(models.PromptUsageEvent.occurred_at >= cutoff)
        if self.tenant_id is not None:
            query = query.filter(models.PromptUsageEvent.tenant_id == self.tenant_id)
        return query

    def _metrics(self, query, period: int | str, as_of: datetime | None = None) -> Metrics:
        cutoff = (as_of or datetime.now(timezone.utc)) - timedelta(days=self._period(period))
        query = query.filter(models.PromptUsageEvent.occurred_at >= cutoff)
        row = query.with_entities(
            func.count(models.PromptUsageEvent.id),
            func.avg(models.PromptUsageEvent.latency_ms),
            func.avg(models.PromptUsageEvent.tokens),
            func.avg(func.cast(models.PromptUsageEvent.fallback, Boolean)),
            func.avg(func.cast(models.PromptUsageEvent.error, Boolean)),
            func.avg(func.cast(models.PromptUsageEvent.engaged, Boolean)),
        ).one()
        count, latency, tokens, fallback, error, engagement = row
        fallback_rate = float(fallback or 0.0)
        error_rate = float(error or 0.0)
        engagement_rate = float(engagement or 0.0)
        quality = (engagement_rate * 60.0) + ((1.0 - fallback_rate) * 25.0) + ((1.0 - error_rate) * 15.0)
        return Metrics(
            usage_count=int(count or 0),
            avg_latency_ms=float(latency or 0.0),
            avg_tokens=float(tokens or 0.0),
            fallback_rate=fallback_rate,
            error_rate=error_rate,
            engagement_rate=engagement_rate,
            quality_score=round(max(0.0, min(100.0, quality)), 2),
            period_days=self._period(period),
        )

    @staticmethod
    def _period(period: int | str) -> int:
        value = int(str(period).rstrip("d"))
        if value not in (7, 30):
            raise ValueError("period must be 7 or 30 days")
        return value

    def _increment_realtime(self, event: models.PromptUsageEvent) -> None:
        if self.redis is None:
            return
        prefix = f"prompt_analytics:{event.tenant_id}"
        for key in (
            f"{prefix}:prompt:{event.prompt_id}:usage",
            f"{prefix}:agent:{event.agent_type}:usage",
            f"{prefix}:channel:{event.channel}:usage",
        ):
            self.redis.incr(key)