"""
dispatch_agent.py

Dispatch Agent for FieldOps Commander AI.

Responsibilities
----------------
- Receive dispatch context.
- Execute the AI dispatch workflow.
- Return a DispatchDecision.

The Dispatch Agent NEVER:

- Assigns technicians.
- Updates the database.
- Changes job status.
- Sends notifications.
- Modifies technician records.
"""

from __future__ import annotations

import logging
import time

from typing import Optional

from app.services.ai.FieldOpsAI.runtime.orchestrator import AIOrchestrator,ai_orchestrator
from app.services.ai.FieldOpsAI.schemas.ai_task import AITask
from app.services.ai.FieldOpsAI.schemas.dispatch import DispatchContext,DispatchDecision


logger = logging.getLogger(__name__)


class DispatchAgent:
    """
    AI agent responsible for dispatch workflow decisions.
    """

    def __init__(
        self,
        orchestrator: Optional[AIOrchestrator] = None,
    ) -> None:
        """
        Initialize the Dispatch Agent.

        Parameters
        ----------
        orchestrator
            Optional orchestrator instance.
            Dependency injection makes testing easier.
        """

        self.orchestrator = orchestrator or ai_orchestrator

    # -------------------------------------------------------------

    def dispatch(
        self,
        context: DispatchContext,
    ) -> DispatchDecision:
        """
        Execute the AI dispatch workflow.

        Parameters
        ----------
        context
            Structured dispatch context.

        Returns
        -------
        DispatchDecision
            Validated dispatch recommendation.

        Raises
        ------
        RuntimeError
            If dispatch processing fails.
        """

        start_time = time.perf_counter()

        logger.info("Dispatch Agent started.")

        try:

            decision = self.orchestrator.execute(
                task=AITask.DISPATCH,
                context=context.model_dump(),
                response_schema=DispatchDecision,
            )

            elapsed = time.perf_counter() - start_time

            logger.info(
                "Dispatch completed in %.2f sec | Job=%s | Technician=%s | Action=%s | Status=%s",
                elapsed,
                decision.job_id,
                decision.technician_id,
                decision.action,
                decision.status,
            )

            return decision

        except Exception as exc:

            logger.exception(
                "Dispatch Agent failed."
            )

            raise RuntimeError(
                "Dispatch Agent failed while generating a workflow recommendation."
            ) from exc