"""Real-time metrics collection for the FieldOps AI runtime."""

from __future__ import annotations

import asyncio
import json
import math
import logging
import statistics
import time
import urllib.request
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Histogram:
    """Bounded histogram retaining observations for percentile queries."""

    buckets: tuple[float, ...] = (0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60)
    values: deque[float] = field(default_factory=lambda: deque(maxlen=10000))
    counts: Counter = field(default_factory=Counter)

    def observe(self, value: float) -> None:
        value = max(0.0, float(value))
        self.values.append(value)
        self.counts[next((bucket for bucket in self.buckets if value <= bucket), "+Inf")] += 1

    def percentile(self, percentile: float) -> float:
        if not self.values:
            return 0.0
        ordered = sorted(self.values)
        index = min(len(ordered) - 1, max(0, math.ceil(len(ordered) * percentile) - 1))
        return round(ordered[index], 6)

    def as_dict(self) -> dict[str, Any]:
        return {
            "count": len(self.values),
            "buckets": {str(key): value for key, value in self.counts.items()},
            "p95": self.percentile(0.95),
            "p99": self.percentile(0.99),
            "avg": round(statistics.fmean(self.values), 6) if self.values else 0.0,
        }


@dataclass
class AgentMetric:
    tasks: int = 0
    successes: int = 0
    failures: int = 0
    execution_time: Histogram = field(default_factory=Histogram)
    last_run: datetime | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "tasks_total": self.tasks,
            "success_rate": self.successes / self.tasks if self.tasks else 0.0,
            "avg_execution_time": self.execution_time.as_dict()["avg"],
            "last_run": self.last_run.isoformat() if self.last_run else None,
        }


@dataclass
class TenantMetric:
    tasks: int = 0
    cost: float = 0.0
    sla_met: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "tasks_total": self.tasks,
            "cost": round(self.cost, 6),
            "sla_compliance_rate": self.sla_met / self.tasks if self.tasks else 0.0,
        }


class MetricsCollector:
    """Collect runtime metrics and optionally publish five-second snapshots."""

    RETENTION_SECONDS = 7 * 24 * 60 * 60
    ALERT_THRESHOLDS = {"error_rate": 0.05, "latency_p95": 5.0, "queue_depth": 5000}

    def __init__(self, *, redis_client: Any = None, webhook_url: str | None = None) -> None:
        self.redis = redis_client
        self.webhook_url = webhook_url
        self.tasks_total = 0
        self.tasks_failed = 0
        self.tasks_by_priority: Counter[str] = Counter()
        self.execution_time = Histogram()
        self.queue_wait_time = Histogram()
        self.queue_depth = 0
        self.active_agents = 0
        self._agents: defaultdict[str, AgentMetric] = defaultdict(AgentMetric)
        self._tenants: defaultdict[str, TenantMetric] = defaultdict(TenantMetric)
        self._snapshots: deque[tuple[float, dict[str, Any]]] = deque()
        self._task: asyncio.Task[None] | None = None
        self._started_at = time.monotonic()

    def record_task(self, *, latency: float, queue_wait: float = 0.0, status: str = "success",
                    priority: str = "normal", agent_id: str | None = None,
                    tenant_id: str | None = None, cost: float = 0.0,
                    sla_met: bool = True, timestamp: datetime | None = None) -> None:
        """Record one completed task. Durations are in seconds."""
        now = timestamp or datetime.now(timezone.utc)
        self.tasks_total += 1
        failed = status.lower() not in {"success", "succeeded", "ok"}
        self.tasks_failed += int(failed)
        self.tasks_by_priority[str(priority)] += 1
        self.execution_time.observe(latency)
        self.queue_wait_time.observe(queue_wait)
        if agent_id is not None:
            metric = self._agents[str(agent_id)]
            metric.tasks += 1
            metric.successes += int(not failed)
            metric.failures += int(failed)
            metric.execution_time.observe(latency)
            metric.last_run = now
        if tenant_id is not None:
            metric = self._tenants[str(tenant_id)]
            metric.tasks += 1
            metric.cost += float(cost)
            metric.sla_met += int(sla_met)

    def set_queue_depth(self, value: int) -> None:
        self.queue_depth = max(0, int(value))

    def set_active_agents(self, value: int) -> None:
        self.active_agents = max(0, int(value))

    def snapshot(self) -> dict[str, Any]:
        snapshot = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tasks_total": self.tasks_total,
            "tasks_failed": self.tasks_failed,
            "tasks_per_second": round(self.tasks_total / max(1.0, time.monotonic() - self._started_at), 6),
            "error_rate": self.tasks_failed / self.tasks_total if self.tasks_total else 0.0,
            "tasks_by_priority": dict(self.tasks_by_priority),
            "execution_time": self.execution_time.as_dict(),
            "queue_wait_time": self.queue_wait_time.as_dict(),
            "queue_depth": self.queue_depth,
            "active_agents": self.active_agents,
            "alerts": self.alerts(),
        }
        return snapshot

    def agent_snapshot(self) -> dict[str, dict[str, Any]]:
        return {key: value.as_dict() for key, value in self._agents.items()}

    def tenant_snapshot(self) -> dict[str, dict[str, Any]]:
        return {key: value.as_dict() for key, value in self._tenants.items()}

    def alerts(self) -> list[dict[str, Any]]:
        snapshot = {"error_rate": self.tasks_failed / self.tasks_total if self.tasks_total else 0.0,
                    "latency_p95": self.execution_time.percentile(0.95), "queue_depth": self.queue_depth}
        return [{"rule": key, "value": snapshot[key], "threshold": threshold}
                for key, threshold in self.ALERT_THRESHOLDS.items() if snapshot[key] > threshold]

    async def flush(self) -> dict[str, Any]:
        """Publish a snapshot to Redis with seven-day retention."""
        snapshot = self.snapshot()
        now = time.time()
        self._snapshots.append((now, snapshot))
        cutoff = now - self.RETENTION_SECONDS
        while self._snapshots and self._snapshots[0][0] < cutoff:
            self._snapshots.popleft()
        if self.redis is not None:
            key = f"fieldops:runtime:metrics:{int(now // 5) * 5}"
            payload = json.dumps(snapshot)
            result = self.redis.setex(key, self.RETENTION_SECONDS, payload)
            if asyncio.iscoroutine(result):
                await result
        if self.webhook_url and snapshot["alerts"]:
            await self.send_alerts(snapshot["alerts"])
        return snapshot

    async def send_alerts(self, alerts: list[dict[str, Any]]) -> None:
        """Send triggered rules to the configured webhook without blocking collection."""
        if not self.webhook_url:
            return
        body = json.dumps({"alerts": alerts}).encode("utf-8")

        def post() -> None:
            request = urllib.request.Request(
                self.webhook_url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=5):
                pass

        try:
            await asyncio.to_thread(post)
        except Exception:
            logger.exception("runtime_metrics_webhook_failed")

    def archive_daily(self, db: Any, *, rollup_date: Any = None) -> Any:
        """Persist the current aggregate and remove PostgreSQL rows older than 90 days."""
        from datetime import date
        from app.models.runtime_metrics import RuntimeMetricRollup

        day = rollup_date or date.today()
        row = RuntimeMetricRollup(
            rollup_date=day,
            tasks_total=self.tasks_total,
            tasks_failed=self.tasks_failed,
            total_cost=sum(metric.cost for metric in self._tenants.values()),
            sla_compliant=sum(metric.sla_met for metric in self._tenants.values()),
            metrics=self.snapshot(),
        )
        db.add(row)
        db.query(RuntimeMetricRollup).filter(
            RuntimeMetricRollup.rollup_date < day - timedelta(days=90)
        ).delete(synchronize_session=False)
        db.commit()
        return row

    async def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run(self) -> None:
        while True:
            await self.flush()
            await asyncio.sleep(5)


runtime_metrics_collector = MetricsCollector()
