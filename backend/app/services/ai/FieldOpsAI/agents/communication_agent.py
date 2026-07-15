"""
communication_agent.py

Communication Agent for FieldOps Commander AI.

Responsibilities
----------------
- Generate customer-facing communication.
- Support Email, SMS, Push Notification, and In-App Notification.
- Follow business tone and branding.
- Return a validated CommunicationDecision.

The Communication Agent NEVER:
- Sends messages.
- Updates the database.
- Changes job status.
- Assigns technicians.
- Makes business decisions.
"""

from __future__ import annotations

import logging
import time

from typing import Optional

from app.services.ai.FieldOpsAI.runtime.orchestrator import AIOrchestrator,ai_orchestrator
from app.services.ai.FieldOpsAI.schemas.ai_task import AITask
from app.services.ai.FieldOpsAI.schemas.communication import CommunicationContext,CommunicationDecision


logger = logging.getLogger(__name__)


class CommunicationAgent:
    """
    AI agent responsible for generating
    customer-facing communication.
    """

    def __init__(
        self,
        orchestrator: Optional[AIOrchestrator] = None,
    ) -> None:
        """
        Initialize the Communication Agent.

        Parameters
        ----------
        orchestrator
            Optional AIOrchestrator instance.
            Dependency injection simplifies testing.
        """

        self.orchestrator = orchestrator or ai_orchestrator

    # -------------------------------------------------------------

    def generate(
        self,
        context: CommunicationContext,
    ) -> CommunicationDecision:
        """
        Generate customer communication.

        Parameters
        ----------
        context
            Structured communication context.

        Returns
        -------
        CommunicationDecision
            Validated AI-generated communication.

        Raises
        ------
        RuntimeError
            If communication generation fails.
        """

        start_time = time.perf_counter()

        logger.info(
            "Communication Agent started for Job %s",
            context.job_id,
        )

        try:

            decision = self.orchestrator.execute(
                task=AITask.COMMUNICATION,
                context=context.model_dump(),
                response_schema=CommunicationDecision,
            )

            elapsed = time.perf_counter() - start_time

            logger.info(
                "Communication generated in %.2f sec | Job=%s | Channel=%s",
                elapsed,
                context.job_id,
                decision.channel,
            )

            return decision

        except Exception as exc:

            logger.exception(
                "Communication Agent failed."
            )

            raise RuntimeError(
                "Communication Agent failed while generating customer communication."
            ) from exc