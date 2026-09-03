"""
AI Runtime Load Tests

Validates runtime scalability under concurrent task execution.

Coverage:
- 100 concurrent task baseline
- p50 / p95 / p99 latency
- throughput
- error rate
- memory usage
- 0 -> 100 ramp over 5 minutes
- 100 concurrent sustained load for 10 minutes
"""

import asyncio
import time
from unittest.mock import MagicMock

import psutil
import pytest
import fakeredis

from app.services.task_queue import PriorityTaskQueue

from app.services.ai.FieldOpsAI.providers.base_provider import ProviderExecutionError
from app.services.ai.FieldOpsAI.providers.provider_failover import (
    ProviderFailoverExecutor,
)
from app.services.ai.FieldOpsAI.runtime.orchestrator import (
    AIOrchestrator,
)
from app.services.ai.FieldOpsAI.schemas.ai_task import AITask
from tests.test_orchestrator_failover import make_isolated_orchestrator

from app.services.ai.FieldOpsAI.runtime.engine import (
    AIRuntimeEngine,
    TaskSpec,
    TaskStatus,
)


pytestmark = pytest.mark.asyncio


# ============================================================================
# LOAD TEST RUNNER
# ============================================================================


async def fast_load_runner(spec: TaskSpec):
    """
    Lightweight runner used for runtime load testing.

    This avoids external AI providers so that the test measures
    Runtime Engine concurrency and scheduling behavior.
    """

    await asyncio.sleep(0.01)

    return {
        "task_id": spec.task_id,
        "index": spec.context["index"],
    }


# ============================================================================
# HELPERS
# ============================================================================


def calculate_percentile(
    values: list[float],
    percentile: float,
) -> float:
    """
    Calculate a percentile using nearest-rank indexing.
    """

    sorted_values = sorted(values)

    if not sorted_values:
        raise ValueError(
            "Cannot calculate percentile from empty data"
        )

    index = max(
        0,
        min(
            len(sorted_values) - 1,
            int(percentile * len(sorted_values)) - 1,
        ),
    )

    return sorted_values[index]


async def run_concurrent_tasks(
    engine: AIRuntimeEngine,
    task_count: int,
):
    """
    Execute a specified number of tasks concurrently.

    Used by the baseline 100-task load test.
    """

    specs = [
        TaskSpec(
            agent_type="load_test_agent",
            tenant_id="load-test-org",
            context={"index": i},
        )
        for i in range(task_count)
    ]

    return await asyncio.gather(
        *(engine.execute_task(spec) for spec in specs)
    )


# ============================================================================
# RAMP LOAD
# ============================================================================


async def ramp_load(
    engine: AIRuntimeEngine,
    target_concurrency: int,
    ramp_duration_seconds: float,
):
    """
    Gradually add tasks from 0 to the target over the requested duration.
    """

    if target_concurrency <= 0:
        raise ValueError(
            "target_concurrency must be greater than 0"
        )

    if ramp_duration_seconds <= 0:
        raise ValueError(
            "ramp_duration_seconds must be greater than 0"
        )

    interval = (
        ramp_duration_seconds / target_concurrency
    )

    running_tasks = []

    for i in range(target_concurrency):

        spec = TaskSpec(
            agent_type="load_test_agent",
            tenant_id="load-test-org",
            context={"index": i},
        )

        running_tasks.append(
            asyncio.create_task(
                engine.execute_task(spec)
            )
        )

        await asyncio.sleep(interval)

    return await asyncio.gather(
        *running_tasks
    )


# ============================================================================
# SUSTAINED LOAD
# ============================================================================


async def run_sustained_load(
    engine: AIRuntimeEngine,
    concurrency: int,
    duration_seconds: int,
    sample_interval_seconds: int = 5,
):
    """
    Keep approximately `concurrency` workers active for the requested
    duration while collecting bounded performance metrics.

    IMPORTANT:
    We do NOT store every TaskResult.

    A 10-minute sustained test can execute millions of tasks.
    Storing every result would make the LOAD TEST itself consume
    several GB of memory and would produce a false memory-leak signal.

    Instead we collect:
    - completed task count
    - succeeded task count
    - failed task count
    - bounded latency samples
    - memory samples
    """

    if concurrency <= 0:
        raise ValueError(
            "concurrency must be greater than 0"
        )

    if duration_seconds <= 0:
        raise ValueError(
            "duration_seconds must be greater than 0"
        )

    if sample_interval_seconds <= 0:
        raise ValueError(
            "sample_interval_seconds must be greater than 0"
        )

    process = psutil.Process()

    # ------------------------------------------------------------------------
    # BOUNDED METRICS
    # ------------------------------------------------------------------------

    completed = 0
    succeeded = 0
    failed = 0

    latency_samples = []

    # Never keep unlimited latency data in memory.
    max_latency_samples = 10_000

    memory_samples = []

    # ------------------------------------------------------------------------
    # END TIME
    # ------------------------------------------------------------------------

    end_time = (
        time.perf_counter()
        + duration_seconds
    )

    # ------------------------------------------------------------------------
    # WORKER
    # ------------------------------------------------------------------------

    async def worker(worker_id: int):
        nonlocal completed
        nonlocal succeeded
        nonlocal failed

        while time.perf_counter() < end_time:

            spec = TaskSpec(
                agent_type="load_test_agent",
                tenant_id="load-test-org",
                context={"index": worker_id},
            )

            result = await engine.execute_task(spec)

            completed += 1

            if result.status == TaskStatus.SUCCEEDED:
                succeeded += 1
            else:
                failed += 1

            if result.duration_seconds is not None:

                # Keep only a bounded number of latency values.
                if len(latency_samples) < max_latency_samples:

                    latency_samples.append(
                        result.duration_seconds
                    )

                else:

                    sample_index = (
                        completed
                        % max_latency_samples
                    )

                    latency_samples[sample_index] = (
                        result.duration_seconds
                    )

    # ------------------------------------------------------------------------
    # MEMORY MONITOR
    # ------------------------------------------------------------------------

    async def memory_monitor():
        """
        Collect process RSS memory periodically.

        Sampling every 5 seconds gives approximately 120 samples
        during a 10-minute test.
        """

        while time.perf_counter() < end_time:

            memory_mb = (
                process.memory_info().rss
                / (1024 * 1024)
            )

            memory_samples.append(
                {
                    "time": time.perf_counter(),
                    "memory_mb": memory_mb,
                }
            )

            await asyncio.sleep(
                sample_interval_seconds
            )

        # Final memory sample.
        memory_mb = (
            process.memory_info().rss
            / (1024 * 1024)
        )

        memory_samples.append(
            {
                "time": time.perf_counter(),
                "memory_mb": memory_mb,
            }
        )

    # ------------------------------------------------------------------------
    # START WORKERS
    # ------------------------------------------------------------------------

    workers = [
        asyncio.create_task(
            worker(i)
        )
        for i in range(concurrency)
    ]

    monitor = asyncio.create_task(
        memory_monitor()
    )

    # Wait for all 100 workers.
    await asyncio.gather(
        *workers
    )

    # Wait for memory monitor to finish naturally.
    try:
        await monitor
    except asyncio.CancelledError:
        pass

    # ------------------------------------------------------------------------
    # RETURN BOUNDED METRICS
    # ------------------------------------------------------------------------

    return {
        "completed": completed,
        "succeeded": succeeded,
        "failed": failed,
        "latencies": latency_samples,
        "memory_samples": memory_samples,
    }


# ============================================================================
# TEST 1 — 100 CONCURRENT TASKS
# ============================================================================


async def test_100_concurrent_tasks_load():
    """
    Execute 100 tasks concurrently.

    Acceptance criteria:
    - 100 tasks submitted
    - 100 tasks completed
    - All tasks succeed
    - Error rate = 0
    - p95 latency < 5 seconds
    - Runtime does not crash
    """

    engine = AIRuntimeEngine(
        max_concurrency=100,
        agent_runner=fast_load_runner,
    )

    process = psutil.Process()

    memory_before_mb = (
        process.memory_info().rss
        / (1024 * 1024)
    )

    start_time = time.perf_counter()

    results = await run_concurrent_tasks(
        engine,
        100,
    )

    total_duration = (
        time.perf_counter()
        - start_time
    )

    memory_after_mb = (
        process.memory_info().rss
        / (1024 * 1024)
    )

    memory_growth_mb = (
        memory_after_mb
        - memory_before_mb
    )

    # ------------------------------------------------------------------------
    # RESULT VALIDATION
    # ------------------------------------------------------------------------

    assert len(results) == 100

    assert all(
        result.status == TaskStatus.SUCCEEDED
        for result in results
    )

    # ------------------------------------------------------------------------
    # LATENCY
    # ------------------------------------------------------------------------

    latencies = [
        result.duration_seconds
        for result in results
        if result.duration_seconds is not None
    ]

    assert len(latencies) == 100

    p50_latency = calculate_percentile(
        latencies,
        0.50,
    )

    p95_latency = calculate_percentile(
        latencies,
        0.95,
    )

    p99_latency = calculate_percentile(
        latencies,
        0.99,
    )

    # ------------------------------------------------------------------------
    # RUNTIME METRICS
    # ------------------------------------------------------------------------

    metrics = engine.metrics()

    # ------------------------------------------------------------------------
    # REPORT
    # ------------------------------------------------------------------------

    print("\n")
    print("=" * 60)
    print("100 CONCURRENT TASK LOAD TEST")
    print("=" * 60)

    print(
        f"Tasks submitted       : "
        f"{metrics['submitted']}"
    )

    print(
        f"Tasks succeeded       : "
        f"{metrics['succeeded']}"
    )

    print(
        f"Tasks failed          : "
        f"{metrics['failed']}"
    )

    print(
        f"Success rate          : "
        f"{metrics['success_rate']:.2%}"
    )

    print(
        f"Error rate            : "
        f"{metrics['error_rate']:.2%}"
    )

    print(
        f"Total duration        : "
        f"{total_duration:.3f}s"
    )

    print(
        f"Average latency       : "
        f"{metrics['avg_latency_seconds']:.3f}s"
    )

    print(
        f"p50 latency           : "
        f"{p50_latency:.3f}s"
    )

    print(
        f"p95 latency           : "
        f"{p95_latency:.3f}s"
    )

    print(
        f"p99 latency           : "
        f"{p99_latency:.3f}s"
    )

    print(
        f"Throughput            : "
        f"{metrics['throughput_tasks_per_second']:.2f} "
        f"tasks/sec"
    )

    print(
        f"Memory before         : "
        f"{memory_before_mb:.2f} MB"
    )

    print(
        f"Memory after          : "
        f"{memory_after_mb:.2f} MB"
    )

    print(
        f"Memory growth         : "
        f"{memory_growth_mb:.2f} MB"
    )

    print("=" * 60)

    # ------------------------------------------------------------------------
    # ACCEPTANCE CRITERIA
    # ------------------------------------------------------------------------

    assert metrics["submitted"] == 100

    assert metrics["succeeded"] == 100

    assert metrics["failed"] == 0

    assert metrics["error_rate"] == 0.0

    assert p95_latency < 5.0, (
        f"p95 latency was {p95_latency:.3f}s; "
        "expected < 5s"
    )


# ============================================================================
# TEST 2 — 0 TO 100 RAMP OVER 5 MINUTES
# ============================================================================


@pytest.mark.slow
async def test_ramp_to_100_concurrent_tasks():
    """
    Ramp from 0 to 100 concurrent tasks over 5 minutes.

    Acceptance criteria:
    - 100 tasks complete successfully
    - No runtime crashes
    - Error rate = 0
    - p95 latency < 5 seconds
    """

    engine = AIRuntimeEngine(
        max_concurrency=100,
        agent_runner=fast_load_runner,
    )

    process = psutil.Process()

    memory_before_mb = (
        process.memory_info().rss
        / (1024 * 1024)
    )

    start_time = time.perf_counter()

    results = await ramp_load(
        engine=engine,
        target_concurrency=100,
        ramp_duration_seconds=300,
    )

    total_duration = (
        time.perf_counter()
        - start_time
    )

    memory_after_mb = (
        process.memory_info().rss
        / (1024 * 1024)
    )

    memory_growth_mb = (
        memory_after_mb
        - memory_before_mb
    )

    # ------------------------------------------------------------------------
    # RESULT VALIDATION
    # ------------------------------------------------------------------------

    assert len(results) == 100

    assert all(
        result.status == TaskStatus.SUCCEEDED
        for result in results
    )

    # ------------------------------------------------------------------------
    # LATENCY
    # ------------------------------------------------------------------------

    latencies = [
        result.duration_seconds
        for result in results
        if result.duration_seconds is not None
    ]

    assert len(latencies) == 100

    p50_latency = calculate_percentile(
        latencies,
        0.50,
    )

    p95_latency = calculate_percentile(
        latencies,
        0.95,
    )

    p99_latency = calculate_percentile(
        latencies,
        0.99,
    )

    # ------------------------------------------------------------------------
    # RUNTIME METRICS
    # ------------------------------------------------------------------------

    metrics = engine.metrics()

    # ------------------------------------------------------------------------
    # REPORT
    # ------------------------------------------------------------------------

    print("\n")
    print("=" * 60)
    print("5-MINUTE RAMP TO 100 CONCURRENT TASKS")
    print("=" * 60)

    print(
        f"Tasks submitted       : "
        f"{metrics['submitted']}"
    )

    print(
        f"Tasks succeeded       : "
        f"{metrics['succeeded']}"
    )

    print(
        f"Tasks failed          : "
        f"{metrics['failed']}"
    )

    print(
        f"Success rate          : "
        f"{metrics['success_rate']:.2%}"
    )

    print(
        f"Error rate            : "
        f"{metrics['error_rate']:.2%}"
    )

    print(
        f"Total duration        : "
        f"{total_duration:.2f}s"
    )

    print(
        f"Average latency       : "
        f"{metrics['avg_latency_seconds']:.3f}s"
    )

    print(
        f"p50 latency           : "
        f"{p50_latency:.3f}s"
    )

    print(
        f"p95 latency           : "
        f"{p95_latency:.3f}s"
    )

    print(
        f"p99 latency           : "
        f"{p99_latency:.3f}s"
    )

    print(
        f"Throughput            : "
        f"{metrics['throughput_tasks_per_second']:.2f} "
        f"tasks/sec"
    )

    print(
        f"Memory before         : "
        f"{memory_before_mb:.2f} MB"
    )

    print(
        f"Memory after          : "
        f"{memory_after_mb:.2f} MB"
    )

    print(
        f"Memory growth         : "
        f"{memory_growth_mb:.2f} MB"
    )

    print("=" * 60)

    # ------------------------------------------------------------------------
    # ACCEPTANCE CRITERIA
    # ------------------------------------------------------------------------

    assert metrics["submitted"] == 100

    assert metrics["succeeded"] == 100

    assert metrics["failed"] == 0

    assert metrics["error_rate"] == 0.0

    assert p95_latency < 5.0, (
        f"p95 latency was {p95_latency:.3f}s; "
        "expected < 5s"
    )


# ============================================================================
# TEST 3 — 100 CONCURRENT SUSTAINED FOR 10 MINUTES
# ============================================================================


@pytest.mark.slow
async def test_100_concurrent_sustained_for_10_minutes():
    """
    Sustain 100 concurrent workers for 10 minutes.

    Acceptance criteria:
    - Runtime remains stable for the full duration
    - Tasks continue completing successfully
    - No crashes
    - Error rate = 0%
    - p95 latency < 5 seconds
    - Memory remains reasonably stable
    """

    engine = AIRuntimeEngine(
        max_concurrency=100,
        agent_runner=fast_load_runner,
    )

    process = psutil.Process()

    memory_before_mb = (
        process.memory_info().rss
        / (1024 * 1024)
    )

    start_time = time.perf_counter()

    load_metrics = await run_sustained_load(
        engine=engine,
        concurrency=100,
        duration_seconds=600,
        sample_interval_seconds=5,
    )

    total_duration = (
        time.perf_counter()
        - start_time
    )

    memory_after_mb = (
        process.memory_info().rss
        / (1024 * 1024)
    )

    memory_growth_mb = (
        memory_after_mb
        - memory_before_mb
    )

    # ------------------------------------------------------------------------
    # EXTRACT LOAD METRICS
    # ------------------------------------------------------------------------

    completed = load_metrics["completed"]

    succeeded = load_metrics["succeeded"]

    failed = load_metrics["failed"]

    latencies = load_metrics["latencies"]

    memory_samples = load_metrics["memory_samples"]

    # ------------------------------------------------------------------------
    # RESULT VALIDATION
    # ------------------------------------------------------------------------

    assert completed > 0

    assert succeeded == completed

    assert failed == 0

    # ------------------------------------------------------------------------
    # LATENCY
    # ------------------------------------------------------------------------

    assert latencies

    p50_latency = calculate_percentile(
        latencies,
        0.50,
    )

    p95_latency = calculate_percentile(
        latencies,
        0.95,
    )

    p99_latency = calculate_percentile(
        latencies,
        0.99,
    )

    # ------------------------------------------------------------------------
    # RUNTIME METRICS
    # ------------------------------------------------------------------------

    metrics = engine.metrics()

    # ------------------------------------------------------------------------
    # MEMORY ANALYSIS
    # ------------------------------------------------------------------------

    assert memory_samples

    memory_values = [
        sample["memory_mb"]
        for sample in memory_samples
    ]

    peak_memory_mb = max(
        memory_values
    )

    minimum_memory_mb = min(
        memory_values
    )

    memory_sample_growth_mb = (
        memory_values[-1]
        - memory_values[0]
        if len(memory_values) >= 2
        else 0.0
    )

    # ------------------------------------------------------------------------
    # THROUGHPUT
    # ------------------------------------------------------------------------

    throughput = (
        completed / total_duration
        if total_duration > 0
        else 0.0
    )

    # ------------------------------------------------------------------------
    # REPORT
    # ------------------------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("10-MINUTE SUSTAINED LOAD TEST")
    print("=" * 70)

    print(
        f"Duration              : "
        f"{total_duration:.2f}s"
    )

    print(
        f"Tasks completed       : "
        f"{completed}"
    )

    print(
        f"Tasks succeeded       : "
        f"{succeeded}"
    )

    print(
        f"Tasks failed          : "
        f"{failed}"
    )

    print(
        f"Success rate          : "
        f"{succeeded / completed:.2%}"
    )

    print(
        f"Error rate            : "
        f"{failed / completed:.2%}"
    )

    print(
        f"p50 latency           : "
        f"{p50_latency:.3f}s"
    )

    print(
        f"p95 latency           : "
        f"{p95_latency:.3f}s"
    )

    print(
        f"p99 latency           : "
        f"{p99_latency:.3f}s"
    )

    print(
        f"Throughput            : "
        f"{throughput:.2f} tasks/sec"
    )

    print(
        f"Memory before         : "
        f"{memory_before_mb:.2f} MB"
    )

    print(
        f"Memory after          : "
        f"{memory_after_mb:.2f} MB"
    )

    print(
        f"Peak memory           : "
        f"{peak_memory_mb:.2f} MB"
    )

    print(
        f"Minimum memory        : "
        f"{minimum_memory_mb:.2f} MB"
    )

    print(
        f"Memory growth         : "
        f"{memory_growth_mb:.2f} MB"
    )

    print(
        f"Sample memory growth  : "
        f"{memory_sample_growth_mb:.2f} MB"
    )

    print(
        f"Memory samples        : "
        f"{len(memory_samples)}"
    )

    print("=" * 70)

    # ------------------------------------------------------------------------
    # ACCEPTANCE CRITERIA
    # ------------------------------------------------------------------------

    assert total_duration >= 590, (
        f"Sustained test ran only "
        f"{total_duration:.2f}s; "
        "expected approximately 600 seconds"
    )

    assert completed > 0

    assert succeeded == completed

    assert failed == 0

    assert p95_latency < 5.0, (
        f"p95 latency was {p95_latency:.3f}s; "
        "expected < 5s"
    )

    # With 5-second sampling, a 10-minute run should produce
    # roughly 120 samples. We require at least 50.
    assert len(memory_samples) >= 50, (
        f"Only {len(memory_samples)} memory samples collected; "
        "expected at least 50"
    )

# ============================================================================
# TEST 4 — 200 TASK SPIKE
# ============================================================================

async def test_200_task_spike_graceful_degradation():
    """
    Submit a sudden spike of 200 concurrent tasks.

    Acceptance criteria:
    - 200 tasks complete
    - No runtime crash
    - No unhandled exceptions
    - p95 latency < 5 seconds
    """

    engine = AIRuntimeEngine(
        max_concurrency=100,
        agent_runner=fast_load_runner,
    )

    start_time = time.perf_counter()

    results = await run_concurrent_tasks(
        engine,
        200,
    )

    total_duration = time.perf_counter() - start_time

    latencies = [
        result.duration_seconds
        for result in results
        if result.duration_seconds is not None
    ]

    p95_latency = calculate_percentile(
        latencies,
        0.95,
    )

    metrics = engine.metrics()

    print("\n")
    print("=" * 60)
    print("200-TASK SPIKE LOAD TEST")
    print("=" * 60)

    print(f"Tasks submitted       : {metrics['submitted']}")
    print(f"Tasks succeeded       : {metrics['succeeded']}")
    print(f"Tasks failed          : {metrics['failed']}")
    print(f"Error rate            : {metrics['error_rate']:.2%}")
    print(f"Total duration        : {total_duration:.3f}s")
    print(f"p95 latency           : {p95_latency:.3f}s")
    print("=" * 60)

    assert len(results) == 200
    assert metrics["submitted"] == 200
    assert metrics["succeeded"] == 200
    assert metrics["failed"] == 0
    assert metrics["error_rate"] == 0.0
    assert p95_latency < 5.0

# ============================================================================
# TEST 5 — 50% AI FAILURE INJECTION / FAILOVER
# ============================================================================

async def failure_injection_runner(task_spec):
    if int(task_spec.task_id.rsplit("-", 1)[-1]) % 2 == 0:
        raise ProviderExecutionError(
            "Simulated retryable AI failure",
            is_retryable=True,
        )

    await asyncio.sleep(0.01)
    return {"task_id": task_spec.task_id}
async def test_50_percent_ai_failure_injection():
    """Verify 50% primary AI failures successfully fail over."""

    mock_config = MagicMock()
    mock_config.provider_fallback_order = [
        "groq",
        "openai",
    ]

    call_counts = {
        "groq": 0,
        "openai": 0,
    }

    class LoadTestProvider:
        def __init__(self, name: str):
            self.name = name

        def provider_name(self) -> str:
            return self.name

        def model_name(self) -> str:
            return "load-test-model"

    class LoadTestFactory:
        @classmethod
        def create_provider(
            cls,
            name: str,
            config=None,
            provider_kwargs=None,
        ):
            return LoadTestProvider(name)

    class LoadTestCircuitBreaker:
        def check_permission(self, provider_name):
            return object()

        def record_success(self, permit):
            pass

        def record_failure(self, permit, error):
            pass

        def release_probe_lock(self, permit):
            pass

    class LoadTestBudgetManager:
        class Config:
            per_request = {
                "general": 4096,
                "sentiment": 4096,
                "sms": 4096,
                "email": 4096,
                "push": 4096,
                "portal": 4096,
            }

        config = Config()

        def reserve(
            self,
            estimated_input_tokens,
            max_output_tokens,
            category,
            provider,
            model,
            tenant_id,
        ):
            return f"load-test-{provider}"

        def reconcile(
            self,
            reservation_id,
            actual_input_tokens,
            actual_output_tokens,
            provider,
        ):
            pass

        def cancel(self, reservation_id, provider):
            pass

    class LoadTestClient:
        def __init__(self, provider):
            self.provider = provider

        def generate_result(
            self,
            task,
            messages,
            context,
        ):
            provider_name = self.provider.provider_name()
            call_counts[provider_name] += 1

            

            # Fail exactly 50% of primary Groq requests.
            if provider_name == "groq" and call_counts["groq"] % 2 == 1:
                error = ProviderExecutionError(
                "Simulated primary AI failure",
                status_code=429,
                is_retryable=True,
            )

                print(
                "INJECTED FAILURE:",
                provider_name,
                call_counts["groq"],
                error.status_code,
                error.is_retryable,
            )

                raise ProviderExecutionError(
                                "Simulated primary AI failure",
                                status_code=429,
                                is_retryable=True,
                            )
        
            from app.services.ai.FieldOpsAI.schemas.provider import (
                GenerationResult,
                UsageStats,
            )
            print("FALLBACK SUCCESS:", provider_name)

            return GenerationResult(
                text='{"summary": "AI success"}',
                provider_name=provider_name,
                model_name="load-test-model",
                usage=UsageStats(
                    prompt_tokens=10,
                    completion_tokens=5,
                    total_tokens=15,
                    request_count=1,
                    latency_ms=10.0,
                    cost_usd=0.0,
                ),
            )

    def client_factory(provider):
        return LoadTestClient(provider)
    
    failover_executor = ProviderFailoverExecutor(
    provider_factory=LoadTestFactory,
    health_monitor=None,
    config=mock_config,
)

    orchestrator = AIOrchestrator(
    failover_executor=failover_executor,
    provider_client_factory=client_factory,
    circuit_breaker=LoadTestCircuitBreaker(),
    budget_manager=LoadTestBudgetManager(),
    provider_cache=MagicMock(get=MagicMock(return_value=None)),
)

    async def execute_one(index):
        return await asyncio.to_thread(
            orchestrator.execute,
            AITask.PLANNING,
            {"job_id": f"load-test-{index}"},
        )

    results = await asyncio.gather(
        *(execute_one(index) for index in range(100)),
        return_exceptions=True,
    )

    failures = [
        result
        for result in results
        if isinstance(result, Exception)
    ]
    if failures:
        print(f"FIRST FAILURE TYPE: {type(failures[0]).__name__}")
        print(f"FIRST FAILURE: {failures[0]!r}")
        print(f"FIRST FAILURE DICT: {getattr(failures[0], '__dict__', {})}")

    print("\n")
    print("=" * 60)
    print("50% AI FAILURE + FAILOVER LOAD TEST")
    print("=" * 60)
    print(f"Tasks submitted : {len(results)}")
    print(f"Final failures   : {len(failures)}")
    print(f"Primary calls    : {call_counts['groq']}")
    print(f"Fallback calls   : {call_counts['openai']}")
    print("=" * 60)

    assert len(results) == 100
    assert len(failures) == 0

    
    

    # Exactly 50 failed Groq requests should use OpenAI fallback.
    assert call_counts["openai"] == 50

async def test_100_concurrent_tasks_through_task_queue():
    """Verify 100 concurrent tasks flow through the Runtime Task Queue."""

    redis = fakeredis.FakeRedis(decode_responses=True)
    task_queue = PriorityTaskQueue(redis)

    engine = AIRuntimeEngine(
        max_concurrency=100,
        task_queue=task_queue,
        agent_runner=fast_load_runner,
    )

    await engine.start()

    try:
        results = await run_concurrent_tasks(engine, 100)

        metrics = engine.metrics()

        print("\n")
        print("=" * 60)
        print("100 CONCURRENT TASKS - QUEUE LOAD TEST")
        print("=" * 60)
        print(f"Tasks submitted : {metrics['submitted']}")
        print(f"Tasks succeeded : {metrics['succeeded']}")
        print(f"Tasks failed    : {metrics['failed']}")
        print(f"Queue depth     : {metrics['queue_depth']}")
        print(f"Error rate      : {metrics['error_rate']}")
        print("=" * 60)

        assert len(results) == 100
        assert metrics["submitted"] == 100
        assert metrics["succeeded"] == 100
        assert metrics["failed"] == 0
        assert metrics["error_rate"] == 0.0
        assert task_queue.total_depth() == 0

    finally:
        await engine.shutdown()

async def test_runtime_metrics_are_accurate_under_load():
    """Verify Runtime Engine metrics match the actual task results."""

    engine = AIRuntimeEngine(
        max_concurrency=100,
        agent_runner=fast_load_runner,
    )

    results = await run_concurrent_tasks(engine, 100)
    metrics = engine.metrics()

    successful_results = [
        result
        for result in results
        if result.status == TaskStatus.SUCCEEDED
    ]

    measured_latencies = [
        result.duration_seconds
        for result in successful_results
        if result.duration_seconds is not None
    ]

    expected_avg_latency = (
        sum(measured_latencies) / len(measured_latencies)
    )

    assert metrics["submitted"] == len(results)
    assert metrics["completed"] == len(successful_results)
    assert metrics["succeeded"] == len(successful_results)
    assert metrics["failed"] == 0
    assert metrics["success_rate"] == 1.0
    assert metrics["error_rate"] == 0.0
    assert metrics["avg_latency_seconds"] == pytest.approx(
        expected_avg_latency,
        abs=0.0001,
    )