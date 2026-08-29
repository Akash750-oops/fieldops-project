"""Persistent daily archive for AI runtime metrics."""

from sqlalchemy import Column, Date, DateTime, Float, Integer, JSON, String, func

from app.database import Base


class RuntimeMetricRollup(Base):
    __tablename__ = "runtime_metric_rollups"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(50), index=True, nullable=True)
    rollup_date = Column(Date, index=True, nullable=False)
    tasks_total = Column(Integer, nullable=False, default=0)
    tasks_failed = Column(Integer, nullable=False, default=0)
    total_cost = Column(Float, nullable=False, default=0.0)
    sla_compliant = Column(Integer, nullable=False, default=0)
    metrics = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
