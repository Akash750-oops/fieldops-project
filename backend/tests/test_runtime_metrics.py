import pytest

from app.runtime.metrics import MetricsCollector


class FakeRedis:
    def __init__(self):
        self.calls = []

    def setex(self, key, ttl, value):
        self.calls.append((key, ttl, value))


def test_metrics_counters_histograms_and_isolation():
    collector = MetricsCollector()
    collector.record_task(latency=1, queue_wait=0.5, priority="high", agent_id="a", tenant_id="t")
    collector.record_task(latency=6, queue_wait=1, status="failed", priority="low", agent_id="b", tenant_id="u", cost=2, sla_met=False)

    snapshot = collector.snapshot()
    assert snapshot["tasks_total"] == 2
    assert snapshot["tasks_failed"] == 1
    assert snapshot["tasks_by_priority"] == {"high": 1, "low": 1}
    assert snapshot["execution_time"]["p95"] == 6.0
    assert snapshot["queue_wait_time"]["buckets"]["1"] == 1
    assert collector.agent_snapshot()["a"]["success_rate"] == 1.0
    assert collector.agent_snapshot()["b"]["success_rate"] == 0.0
    assert collector.tenant_snapshot()["t"]["tasks_total"] == 1
    assert collector.tenant_snapshot()["u"]["sla_compliance_rate"] == 0.0


def test_alert_thresholds():
    collector = MetricsCollector()
    collector.record_task(latency=6, status="failed")
    collector.set_queue_depth(5001)
    assert {alert["rule"] for alert in collector.alerts()} == {
        "error_rate", "latency_p95", "queue_depth"
    }


@pytest.mark.asyncio
async def test_redis_snapshot_has_seven_day_ttl():
    redis = FakeRedis()
    collector = MetricsCollector(redis_client=redis)
    await collector.flush()
    assert redis.calls[0][1] == 7 * 24 * 60 * 60
