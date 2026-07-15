"""
planning_agent.py

Planning Agent for FieldOps Commander AI.

Responsibilities
----------------
- Receive customer request.
- Receive technician candidates.
- Build planning context.
- Execute AI planning workflow.
- Return a PlanningDecision.

The Planning Agent NEVER:
- Updates the database
- Assigns technicians
- Sends notifications
- Modifies jobs
"""

from __future__ import annotations

import logging
import time

from typing import Optional

from app.services.ai.FieldOpsAI.runtime.orchestrator import AIOrchestrator,ai_orchestrator
from app.services.ai.FieldOpsAI.schemas.planning import PlanningContext,PlanningDecision
from app.services.ai.FieldOpsAI.schemas.ai_task import AITask

logger = logging.getLogger(__name__)


class PlanningAgent:
    """
    AI agent responsible for technician assignment recommendations.
    """

    def __init__(
        self,
        orchestrator: Optional[AIOrchestrator] = None,
    ) -> None:
        """
        Initialize the Planning Agent.

        Parameters
        ----------
        orchestrator:
            Optional orchestrator instance.
            Dependency injection makes testing much easier.
        """

        self.orchestrator =orchestrator or ai_orchestrator 

    # -------------------------------------------------------------

    def plan(
        self,
        context: PlanningContext,
    ) -> PlanningDecision:
        """
        Execute AI planning.

        Parameters
        ----------
        context
            Structured planning context.

        Returns
        -------
        PlanningDecision
            Validated planning recommendation.

        Raises
        ------
        RuntimeError
            If AI planning fails.
        """

        start_time = time.perf_counter()

        logger.info("Planning Agent started.")

        try:

            decision = self.orchestrator.execute(
                task=AITask.PLANNING,
                context=context.model_dump(),
                response_schema=PlanningDecision,
            )

            elapsed = time.perf_counter() - start_time

            if decision.recommended_technicians:
                top = decision.recommended_technicians[0]

                logger.info(
                    "Planning completed in %.2f sec | Top Technician=%s | Confidence=%.2f",
                    elapsed,
                    top.technician_id,
                    top.confidence,
                )
            else:
                logger.info(
                    "Planning completed in %.2f sec | Action=%s",
                    elapsed,
                    decision.action,
                )

            return decision

        except Exception as exc:

            logger.exception(
                "Planning Agent failed."
            )

            raise RuntimeError(
                "Planning Agent failed while generating technician recommendations."
            ) from exc