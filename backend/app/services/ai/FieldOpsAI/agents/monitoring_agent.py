"""
monitoring_agent.py

Monitoring Agent for FieldOps Commander AI,
migrated to inherit from BaseAgent.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

from app.services.ai.FieldOpsAI.agents.base import BaseAgent
from app.services.ai.FieldOpsAI.runtime.orchestrator import (
    AIOrchestrator,
    ai_orchestrator,
)
from app.services.ai.FieldOpsAI.schemas.agent_config import AgentConfig
from app.services.ai.FieldOpsAI.schemas.ai_task import AITask
from app.services.ai.FieldOpsAI.schemas.monitoring import (
    MonitoringContext,
    MonitoringDecision,
)

logger = logging.getLogger(__name__)


class MonitoringAgent(BaseAgent[MonitoringDecision]):
    """
    AI agent responsible for monitoring active jobs
    and recommending operational actions.
    """

    def __init__(
        self,
        config: AgentConfig,
        orchestrator: Optional[AIOrchestrator] = None,
    ) -> None:
        """
        Initialize the Monitoring Agent.
        """

        if config.agent_type != AITask.MONITORING:
            raise ValueError(
                "MonitoringAgent requires an AITask.MONITORING configuration."
            )

        super().__init__(config)

        self.orchestrator = (
            ai_orchestrator
            if orchestrator is None
            else orchestrator
        )

    async def run(
        self,
        context: dict[str, Any],
    ) -> MonitoringDecision:
        """
        Execute the AI monitoring task.

        The synchronous AIOrchestrator.execute call is moved to
        a worker thread so the async event loop is not blocked.
        """

        start_time = time.perf_counter()

        logger.info("Monitoring Agent run started.")

        monitoring_context = MonitoringContext.model_validate(context)

        decision = await asyncio.to_thread(
            self.orchestrator.execute,
            task=AITask.MONITORING,
            context=monitoring_context.model_dump(mode="json"),
            response_schema=MonitoringDecision,
        )

        elapsed = time.perf_counter() - start_time

        logger.info(
            "Monitoring completed in %.2f sec | Job=%s | Action=%s | Risk=%s",
            elapsed,
            monitoring_context.job.job_id,
            decision.action,
            decision.risk_level,
        )

        return decision

    def monitor(
        self,
        context: MonitoringContext,
    ) -> MonitoringDecision:
        """
        Compatibility adapter for legacy synchronous callers.

        The internal execution path uses BaseAgent.execute().
        """

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass
        else:
            raise RuntimeError(
                "monitor() cannot be called from an active event loop. "
                "Use the asynchronous AgentLifecycle / execute path instead."
            )

        exec_context = context.model_dump(mode="json")
        exec_context["tenant_id"] = self.tenant_id

        async def _run_wrapped():
            if not self.is_setup:
                await self.setup()

            return await self.execute(exec_context)

        return asyncio.run(_run_wrapped())
