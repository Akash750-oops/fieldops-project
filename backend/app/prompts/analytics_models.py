from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Index, Integer, JSON, String

from app.database import Base


class PromptUsageEvent(Base):
    __tablename__ = "prompt_usage_events"

    id = Column(String(36), primary_key=True)
    prompt_id = Column(Integer, nullable=False, index=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    agent_type = Column(String(50), nullable=False, index=True)
    channel = Column(String(20), nullable=False, index=True)
    latency_ms = Column(Float, nullable=False)
    tokens = Column(Integer, nullable=False)
    fallback = Column(Boolean, nullable=False, default=False)
    error = Column(Boolean, nullable=False, default=False)
    engaged = Column(Boolean, nullable=True)
    occurred_at = Column(DateTime(timezone=True), nullable=False, index=True)

    __table_args__ = (Index("idx_prompt_usage_tenant_time", "tenant_id", "occurred_at"),)


class PromptAnalyticsAggregate(Base):
    __tablename__ = "prompt_analytics_aggregates"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    dimension = Column(String(20), nullable=False)
    dimension_key = Column(String(100), nullable=False)
    period_days = Column(Integer, nullable=False)
    metrics = Column(JSON, nullable=False, default=dict)
    calculated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (Index("uq_prompt_analytics_dimension", "tenant_id", "dimension", "dimension_key", "period_days", unique=True),)