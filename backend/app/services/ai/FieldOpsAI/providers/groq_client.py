"""
groq_client.py

Provider-execution client for FieldOps Commander AI.

Responsibilities
----------------
- Execute AI requests using the configured provider.
- Return the raw provider response.
- Translate provider failures into a safe application error.

The client never:

- Builds prompts
- Renders Jinja2 templates
- Selects fallback communication
- Restores placeholders
- Parses structured responses
- Updates the database
- Sends notifications

Fallback selection belongs to the business workflow, such as
CommunicationService.
"""

from __future__ import annotations

import logging

from typing import Any, Dict, List

from app.services.ai.FieldOpsAI.providers.base_provider import (
    BaseAIProvider,
)
from app.services.ai.FieldOpsAI.providers.provider_factory import (
    ProviderFactory,
)
from app.services.ai.FieldOpsAI.schemas.ai_task import (
    AITask,
)


logger = logging.getLogger(__name__)


class AIProviderExecutionError(RuntimeError):
    """
    Raised when the configured AI provider cannot return a
    usable text response.

    The public exception message deliberately excludes provider
    response content, API keys, prompts, and customer data.
    """


class GroqClient:
    """
    Execute requests through the configured AI provider.

    The class name is retained for compatibility with the
    existing orchestrator. ProviderFactory may later return
    another provider without changing this interface.
    """

    def __init__(
        self,
        *,
        provider: BaseAIProvider | None = None,
    ) -> None:
        """
        Initialize the provider client.

        Dependency injection allows tests to use a fake provider
        without making a real Groq request.
        """

        self.provider = (
            provider
            if provider is not None
            else ProviderFactory.create_provider()
        )

    # ---------------------------------------------------------

    def generate(
        self,
        task: AITask,
        messages: List[Dict[str, str]],
        context: Dict[str, Any],
    ) -> str:
        """
        Execute one provider request.

        Parameters
        ----------
        task
            AI task being executed.

            It is retained for orchestration compatibility and
            safe operational logging.

        messages
            Sanitized system and user messages sent to the
            provider.

        context
            Sanitized structured context.

            The client deliberately does not use or log this
            value. Prompt construction belongs to the
            orchestrator.

        Returns
        -------
        str
            Non-empty raw provider response.

        Raises
        ------
        AIProviderExecutionError
            When provider execution fails or returns an invalid
            response.
        """

        if not isinstance(
            task,
            AITask,
        ):
            raise TypeError(
                "task must be an AITask."
            )

        if not isinstance(
            messages,
            list,
        ) or not messages:
            raise ValueError(
                "messages must be a non-empty list."
            )

        if not isinstance(
            context,
            dict,
        ):
            raise TypeError(
                "context must be a dictionary."
            )

        # The sanitized context is accepted only to preserve the
        # current orchestrator contract. The provider receives
        # messages only.
        _ = context

        provider_name = self._safe_provider_name()

        logger.info(
            "Executing AI provider request. "
            "Provider=%s Task=%s",
            provider_name,
            task.value,
        )

        try:
            response = (
                self.provider.generate_completion(
                    messages=messages
                )
            )

        except Exception as exc:
            # Do not log the provider exception text here.
            # Provider errors may contain request details,
            # response bodies, or infrastructure information.
            logger.warning(
                "AI provider execution failed. "
                "Provider=%s Task=%s",
                provider_name,
                task.value,
            )

            raise AIProviderExecutionError(
                "AI provider execution failed."
            ) from exc

        if not isinstance(
            response,
            str,
        ):
            raise AIProviderExecutionError(
                "AI provider returned an invalid response."
            )

        normalized_response = response.strip()

        if not normalized_response:
            raise AIProviderExecutionError(
                "AI provider returned an empty response."
            )

        logger.info(
            "AI provider request completed. "
            "Provider=%s Task=%s",
            provider_name,
            task.value,
        )

        return normalized_response

    # ---------------------------------------------------------

    def _safe_provider_name(
        self,
    ) -> str:
        """
        Return a safe provider name for operational logging.

        Provider metadata failures must never prevent request
        execution.
        """

        try:
            provider_name = (
                self.provider.provider_name()
            )

        except Exception:
            return "unknown"

        if not isinstance(
            provider_name,
            str,
        ):
            return "unknown"

        normalized_name = provider_name.strip()

        return (
            normalized_name
            if normalized_name
            else "unknown"
        )