"""
orchestrator.py

Central orchestration layer for the FieldOps Commander AI.

Responsibilities
----------------
- Build the complete system prompt.
- Load the task-specific prompt.
- Sanitize PII before external AI provider calls.
- Validate that no detectable PII remains in user prompts.
- Send the sanitized request to the configured provider.
- Restore permitted placeholder values locally.
- Track token usage.
- Parse and validate structured AI responses.

The orchestrator contains NO business logic.

Important privacy rule
----------------------
The original context must never be passed to Groq or another
external AI provider. Only sanitized context and prompts may
cross the provider boundary.
"""

from __future__ import annotations

import json
import logging

from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel

from app.services.ai.pii_sanitizer import (
    PIISanitizer,
    PIILeakageError,
    PlaceholderMap,
    pii_sanitizer,
)
from app.services.ai.FieldOpsAI.providers.groq_client import GroqClient
from app.services.ai.FieldOpsAI.runtime.prompt_builder import PromptBuilder
from app.services.ai.FieldOpsAI.runtime.response_parser import ResponseParser
from app.services.ai.FieldOpsAI.runtime.runtime_interface import RuntimeInterface
from app.services.ai.FieldOpsAI.runtime.token_tracker import token_tracker
from app.services.ai.FieldOpsAI.schemas.ai_task import AITask


logger = logging.getLogger(__name__)


class AIOrchestrator(RuntimeInterface):
    """
    Coordinate prompt construction, privacy protection,
    provider execution, restoration, and response validation.
    """

    def __init__(
        self,
        *,
        client: GroqClient | None = None,
        sanitizer: PIISanitizer | None = None,
        prompt_builder: PromptBuilder | None = None,
        response_parser: ResponseParser | None = None,
    ) -> None:
        """
        Initialize the AI orchestrator.

        Dependency injection is supported so tests can provide
        fake clients without making real Groq API requests.
        """

        self.prompt_builder = (
            prompt_builder
            if prompt_builder is not None
            else PromptBuilder()
        )

        self.client = (
            client
            if client is not None
            else GroqClient()
        )

        self.pii_sanitizer = (
            sanitizer
            if sanitizer is not None
            else pii_sanitizer
        )

        self.token_tracker = token_tracker

        self.response_parser = (
            response_parser
            if response_parser is not None
            else ResponseParser()
        )

    # ---------------------------------------------------------

    def _load_task_prompt(
        self,
        task: AITask,
    ) -> str:
        """
        Load the task-specific prompt.

        Examples
        --------
        planning       -> prompts/planning.md
        dispatch       -> prompts/dispatch.md
        monitoring     -> prompts/monitoring.md
        sentiment      -> prompts/sentiment.md
        communication  -> prompts/communication.md
        closure        -> prompts/closure.md
        """

        prompt_path = (
            Path(__file__).parent.parent
            / "prompts"
            / f"{task.value}.md"
        )

        if not prompt_path.exists():
            raise FileNotFoundError(
                f"Task prompt not found: {prompt_path}"
            )

        return prompt_path.read_text(
            encoding="utf-8"
        )

    # ---------------------------------------------------------

    def execute(
        self,
        task: AITask,
        context: Dict[str, Any],
        response_schema: Optional[
            Type[BaseModel]
        ] = None,
    ) -> str | BaseModel:
        """
        Execute an AI task using sanitized data.

        Parameters
        ----------
        task
            AI task being executed.

        context
            Original structured backend context.

            This original dictionary remains inside the
            FieldOps backend. It is never passed directly
            to the provider client.

        response_schema
            Optional Pydantic schema used to validate the
            restored AI response.

        Returns
        -------
        str | BaseModel
            Restored raw response or validated Pydantic model.

        Raises
        ------
        PIILeakageError
            When detectable PII remains in the user prompt.

        RuntimeError
            When provider execution or response processing fails.
        """

        placeholder_map: PlaceholderMap | None = None

        try:
            logger.info(
                "Starting AI task '%s'.",
                task.value,
            )

            # -------------------------------------------------
            # 1. Build static system instructions
            # -------------------------------------------------

            system_prompt = self.prompt_builder.build()

            system_prompt += (
                "\n\n"
                + self._load_task_prompt(
                    task
                )
            )

            # -------------------------------------------------
            # 2. Sanitize structured context
            # -------------------------------------------------

            sanitization_result = (
                self.pii_sanitizer.sanitize(
                    context
                )
            )

            sanitized_context = (
                sanitization_result.sanitized_data
            )

            placeholder_map = (
                sanitization_result.placeholder_map
            )

            if not isinstance(
                sanitized_context,
                dict,
            ):
                raise TypeError(
                    "Sanitized AI context must be a dictionary."
                )

            logger.info(
                "Structured context sanitized for task '%s'. "
                "Replacement count: %s.",
                task.value,
                sanitization_result.replacement_count,
            )

            # -------------------------------------------------
            # 3. Build prompt from sanitized context only
            # -------------------------------------------------

            user_prompt = self._build_user_prompt(
                task=task,
                context=sanitized_context,
            )

            # -------------------------------------------------
            # 4. Run final prompt scan and validation
            # -------------------------------------------------

            (
                sanitized_user_prompt,
                placeholder_map,
            ) = self.pii_sanitizer.sanitize_prompt(
                prompt=user_prompt,
                placeholder_map=placeholder_map,
            )

            messages: List[Dict[str, str]] = [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": sanitized_user_prompt,
                },
            ]

            # -------------------------------------------------
            # 5. Check token budget
            # -------------------------------------------------

            estimated_tokens = (
                len(system_prompt.split())
                + len(
                    sanitized_user_prompt.split()
                )
            )

            if not self.token_tracker.can_make_request(
                estimated_tokens
            ):
                raise RuntimeError(
                    "Daily AI token budget exceeded."
                )

            logger.info(
                "Sending sanitized request to AI provider "
                "for task '%s'.",
                task.value,
            )

            # -------------------------------------------------
            # 6. Call provider using sanitized data only
            # -------------------------------------------------

            response = self.client.generate(
                task=task,
                messages=messages,
                context=sanitized_context,
            )

            if not isinstance(
                response,
                str,
            ):
                raise TypeError(
                    "AI provider response must be a string."
                )

            logger.info(
                "AI response received successfully "
                "for task '%s'.",
                task.value,
            )

            # -------------------------------------------------
            # 7. Restore placeholders locally
            # -------------------------------------------------

            restored_response = (
                self.pii_sanitizer.restore_data(
                    data=response,
                    placeholder_map=placeholder_map,
                    clear_mapping=False,
                )
            )

            if not isinstance(
                restored_response,
                str,
            ):
                raise TypeError(
                    "Restored AI response must be a string."
                )

            # -------------------------------------------------
            # 8. Record token usage
            # -------------------------------------------------

            used_tokens = (
                estimated_tokens
                + len(response.split())
            )

            self.token_tracker.record_usage(
                used_tokens
            )

            # -------------------------------------------------
            # 9. Validate structured response
            # -------------------------------------------------

            if response_schema is not None:
                logger.info(
                    "Validating AI response using schema '%s'.",
                    response_schema.__name__,
                )

                return self.response_parser.parse(
                    restored_response,
                    response_schema,
                )

            return restored_response

        except PIILeakageError:
            # PIILeakageError deliberately contains category
            # names only. It does not expose the private value.
            logger.exception(
                "AI request blocked because PII validation "
                "failed for task '%s'.",
                task.value,
            )

            raise

        except Exception as exc:
            logger.exception(
                "AI orchestration failed for task '%s'.",
                task.value,
            )

            raise RuntimeError(
                "AI orchestration failed for "
                f"task '{task.value}'."
            ) from exc

        finally:
            # The mapping must never remain in memory after
            # this request completes or fails.
            if placeholder_map is not None:
                placeholder_map.clear()

    # ---------------------------------------------------------

    @staticmethod
    def _build_user_prompt(
        task: AITask,
        context: Dict[str, Any],
    ) -> str:
        """
        Build the task user prompt.

        The context passed here must already be sanitized.
        Task-specific behavior remains inside prompts/<task>.md.
        """

        context_text = json.dumps(
            context,
            indent=2,
            ensure_ascii=False,
            default=str,
        )

        return (
            f"TASK:\n"
            f"{task.value}\n\n"
            f"CONTEXT:\n"
            f"{context_text}\n\n"
            "IMPORTANT INSTRUCTIONS\n"
            "----------------------\n"
            "1. Return ONLY a valid JSON object.\n"
            "2. Do NOT use markdown.\n"
            "3. Do NOT explain your answer.\n"
            "4. Do NOT include headings.\n"
            "5. Do NOT include bullet points.\n"
            "6. Do NOT wrap the JSON inside ```json.\n"
            "7. Follow the schema defined in the system "
            "prompt exactly.\n"
            "8. Use ONLY the information provided in CONTEXT.\n"
            "9. Never invent facts, IDs, names, dates, "
            "or values.\n"
            "10. If required information is missing, respond "
            "according to the task schema.\n\n"
            "Return ONLY the JSON object."
        )

    # ---------------------------------------------------------

    def runtime_name(
        self,
    ) -> str:
        """
        Return the active runtime name.
        """

        return "FieldOps AI Runtime (Groq)"

    # ---------------------------------------------------------

    def health_check(
        self,
    ) -> bool:
        """
        Verify that the runtime was initialized.
        """

        try:
            return (
                self.client is not None
                and self.pii_sanitizer is not None
            )

        except Exception:
            return False


ai_orchestrator = AIOrchestrator()