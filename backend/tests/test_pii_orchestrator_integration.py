"""
test_pii_orchestrator_integration.py

Integration tests between AIOrchestrator and PIISanitizer.

These tests prove that:

- Real PII is sanitized before the provider is called.
- The provider receives only placeholder-based context.
- The provider receives only a sanitized user prompt.
- Placeholder values are restored locally.
- PII leakage blocks the provider call.
- Request-scoped mappings are cleared after success or failure.

No real Groq API call is made in these tests.
"""

from __future__ import annotations

import copy
import json

from typing import Any

import pytest
from pydantic import BaseModel

from app.services.ai.pii_sanitizer import (
    PIICategory,
    PIILeakageError,
    PIISanitizer,
    PlaceholderMap,
    SanitizationResult,
)
from app.services.ai.FieldOpsAI.runtime.orchestrator import (
    AIOrchestrator,
)
from app.services.ai.FieldOpsAI.schemas.ai_task import (
    AITask,
)


# ==========================================================
# Test Response Schema
# ==========================================================


class RestoredAIResponse(BaseModel):
    """
    Small response schema used only by these tests.
    """

    message: str


# ==========================================================
# Fake Prompt Builder
# ==========================================================


class StaticPromptBuilder:
    """
    Avoid loading the complete production system prompt.

    This keeps the test focused on privacy behavior.
    """

    def build(self) -> str:
        return (
            "You are the FieldOps AI. "
            "Return valid JSON only."
        )


# ==========================================================
# Tracking Sanitizer
# ==========================================================


class TrackingPIISanitizer(PIISanitizer):
    """
    PIISanitizer that exposes its latest request map to tests.

    This is used only to verify that the orchestrator clears
    request-scoped sensitive data after execution.
    """

    def __init__(self) -> None:
        super().__init__()

        self.last_placeholder_map: (
            PlaceholderMap | None
        ) = None

    def sanitize(
        self,
        data: Any,
    ) -> SanitizationResult:
        result = super().sanitize(data)

        self.last_placeholder_map = (
            result.placeholder_map
        )

        return result


# ==========================================================
# Fake Provider Clients
# ==========================================================


class RecordingClient:
    """
    Fake provider client that records exactly what it receives.

    It never communicates with Groq or another external API.
    """

    def __init__(
        self,
        response: str,
    ) -> None:
        self.response = response

        self.call_count = 0

        self.received_task: AITask | None = None

        self.received_messages: (
            list[dict[str, str]] | None
        ) = None

        self.received_context: (
            dict[str, Any] | None
        ) = None

    def generate(
        self,
        task: AITask,
        messages: list[dict[str, str]],
        context: dict[str, Any],
    ) -> str:
        self.call_count += 1

        self.received_task = task

        self.received_messages = copy.deepcopy(
            messages
        )

        self.received_context = copy.deepcopy(
            context
        )

        return self.response


class FailingClient(RecordingClient):
    """
    Fake provider that simulates an external AI failure.
    """

    def __init__(self) -> None:
        super().__init__(
            response="",
        )

    def generate(
        self,
        task: AITask,
        messages: list[dict[str, str]],
        context: dict[str, Any],
    ) -> str:
        self.call_count += 1

        self.received_task = task

        self.received_messages = copy.deepcopy(
            messages
        )

        self.received_context = copy.deepcopy(
            context
        )

        raise RuntimeError(
            "Simulated provider failure."
        )


class NeverCalledClient(RecordingClient):
    """
    Fake client that fails the test if it is ever called.
    """

    def __init__(self) -> None:
        super().__init__(
            response="",
        )

    def generate(
        self,
        task: AITask,
        messages: list[dict[str, str]],
        context: dict[str, Any],
    ) -> str:
        self.call_count += 1

        raise AssertionError(
            "Provider must not be called after "
            "PII validation fails."
        )


# ==========================================================
# Sanitizer Used to Simulate a Leakage Block
# ==========================================================


class BlockingSanitizer(
    TrackingPIISanitizer
):
    """
    Simulates final-prompt validation detecting remaining PII.
    """

    def sanitize_prompt(
        self,
        prompt: str,
        placeholder_map: PlaceholderMap | None = None,
    ) -> tuple[str, PlaceholderMap]:
        raise PIILeakageError(
            {
                PIICategory.EMAIL,
            }
        )


# ==========================================================
# Helpers
# ==========================================================


def build_orchestrator(
    *,
    client: RecordingClient,
    sanitizer: PIISanitizer,
    monkeypatch: pytest.MonkeyPatch,
) -> AIOrchestrator:
    """
    Build an isolated orchestrator using fake dependencies.
    """

    orchestrator = AIOrchestrator(
        client=client,  # type: ignore[arg-type]
        sanitizer=sanitizer,
        prompt_builder=StaticPromptBuilder(),  # type: ignore[arg-type]
    )

    # Prevent this test from depending on physical Markdown
    # task-prompt files. Prompt-file behavior is tested
    # separately from privacy behavior.
    monkeypatch.setattr(
        orchestrator,
        "_load_task_prompt",
        lambda task: (
            "Generate a safe FieldOps communication response."
        ),
    )

    # Prevent previous tests from affecting the token budget.
    orchestrator.token_tracker.reset()

    return orchestrator


def private_values() -> tuple[str, ...]:
    """
    Return every real sensitive value used in these tests.
    """

    return (
        "Ruby Devi",
        "Kumar Raj",
        "+91 9876543210",
        "ruby@example.com",
        "123 Main Street",
        "JOB-1001",
        "13.0827, 80.2707",
    )


# ==========================================================
# Successful Provider-Boundary Test
# ==========================================================


def test_orchestrator_sends_zero_real_pii_to_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    The provider must receive only placeholders, never real PII.
    """

    original_context: dict[str, Any] = {
        "customer_name": "Ruby Devi",
        "technician_name": "Kumar Raj",
        "customer_phone": "+91 9876543210",
        "customer_email": "ruby@example.com",
        "service_address": "123 Main Street",
        "job_id": "JOB-1001",
        "technician_location": (
            "13.0827, 80.2707"
        ),
        "job_status": "ASSIGNED",
    }

    original_snapshot = copy.deepcopy(
        original_context
    )

    provider_response = json.dumps(
        {
            "message": (
                "Hello {{customer_name}}, "
                "{{technician_name}} is assigned "
                "to {{job_id}}."
            ),
        }
    )

    client = RecordingClient(
        response=provider_response,
    )

    sanitizer = TrackingPIISanitizer()

    orchestrator = build_orchestrator(
        client=client,
        sanitizer=sanitizer,
        monkeypatch=monkeypatch,
    )

    result = orchestrator.execute(
        task=AITask.COMMUNICATION,
        context=original_context,
        response_schema=RestoredAIResponse,
    )

    # ------------------------------------------------------
    # Provider was called exactly once
    # ------------------------------------------------------

    assert client.call_count == 1

    assert (
        client.received_task
        == AITask.COMMUNICATION
    )

    assert (
        client.received_context
        is not None
    )

    assert (
        client.received_messages
        is not None
    )

    # ------------------------------------------------------
    # Provider context contains expected placeholders
    # ------------------------------------------------------

    provider_context = (
        client.received_context
    )

    assert (
        provider_context["customer_name"]
        == "{{customer_name}}"
    )

    assert (
        provider_context["technician_name"]
        == "{{technician_name}}"
    )

    assert (
        provider_context["customer_phone"]
        == "{{customer_phone}}"
    )

    assert (
        provider_context["customer_email"]
        == "{{customer_email}}"
    )

    assert (
        provider_context["service_address"]
        == "{{service_address}}"
    )

    assert (
        provider_context["job_id"]
        == "{{job_id}}"
    )

    assert (
        provider_context[
            "technician_location"
        ]
        == "{{technician_location}}"
    )

    # Non-PII business fields remain usable.
    assert (
        provider_context["job_status"]
        == "ASSIGNED"
    )

    # ------------------------------------------------------
    # No private value exists in provider context
    # ------------------------------------------------------

    serialized_provider_context = json.dumps(
        provider_context,
        ensure_ascii=False,
        default=str,
    )

    for private_value in private_values():
        assert (
            private_value
            not in serialized_provider_context
        )

    # ------------------------------------------------------
    # No private value exists in provider messages
    # ------------------------------------------------------

    serialized_messages = json.dumps(
        client.received_messages,
        ensure_ascii=False,
        default=str,
    )

    for private_value in private_values():
        assert private_value not in serialized_messages

    # User prompt must contain placeholders.
    user_message = next(
        message["content"]
        for message in client.received_messages
        if message["role"] == "user"
    )

    assert "{{customer_name}}" in user_message
    assert "{{technician_name}}" in user_message
    assert "{{customer_phone}}" in user_message
    assert "{{customer_email}}" in user_message
    assert "{{service_address}}" in user_message
    assert "{{job_id}}" in user_message
    assert "{{technician_location}}" in user_message

    # ------------------------------------------------------
    # Placeholder values are restored only after return
    # ------------------------------------------------------

    assert isinstance(
        result,
        RestoredAIResponse,
    )

    assert result.message == (
        "Hello Ruby Devi, "
        "Kumar Raj is assigned to JOB-1001."
    )

    # The original backend context was not modified.
    assert original_context == original_snapshot

    # The request-scoped map was cleared by finally.
    assert (
        sanitizer.last_placeholder_map
        is not None
    )

    assert len(
        sanitizer.last_placeholder_map
    ) == 0

    assert (
        sanitizer.last_placeholder_map.values
        == {}
    )


# ==========================================================
# Leakage-Blocking Test
# ==========================================================


def test_orchestrator_blocks_provider_when_validation_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A privacy validation failure must stop the provider call.
    """

    client = NeverCalledClient()

    sanitizer = BlockingSanitizer()

    orchestrator = build_orchestrator(
        client=client,
        sanitizer=sanitizer,
        monkeypatch=monkeypatch,
    )

    with pytest.raises(
        PIILeakageError
    ) as exc_info:
        orchestrator.execute(
            task=AITask.COMMUNICATION,
            context={
                "customer_name": "Ruby Devi",
                "customer_email": (
                    "ruby@example.com"
                ),
            },
        )

    assert (
        PIICategory.EMAIL
        in exc_info.value.categories
    )

    assert client.call_count == 0

    # Mapping must also be cleared when validation fails.
    assert (
        sanitizer.last_placeholder_map
        is not None
    )

    assert len(
        sanitizer.last_placeholder_map
    ) == 0


# ==========================================================
# Provider-Failure Cleanup Test
# ==========================================================


def test_orchestrator_clears_mapping_after_provider_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Sensitive values must be removed from memory even when
    the external provider fails.
    """

    client = FailingClient()

    sanitizer = TrackingPIISanitizer()

    orchestrator = build_orchestrator(
        client=client,
        sanitizer=sanitizer,
        monkeypatch=monkeypatch,
    )

    with pytest.raises(
        RuntimeError,
        match="AI orchestration failed",
    ):
        orchestrator.execute(
            task=AITask.COMMUNICATION,
            context={
                "customer_name": "Ruby Devi",
                "customer_phone": (
                    "+91 9876543210"
                ),
                "job_id": "JOB-1001",
            },
        )

    assert client.call_count == 1

    # Even the failing provider received sanitized data.
    assert (
        client.received_context
        is not None
    )

    assert (
        client.received_context[
            "customer_name"
        ]
        == "{{customer_name}}"
    )

    assert (
        client.received_context[
            "customer_phone"
        ]
        == "{{customer_phone}}"
    )

    assert (
        client.received_context["job_id"]
        == "{{job_id}}"
    )

    serialized_provider_data = json.dumps(
        {
            "messages": client.received_messages,
            "context": client.received_context,
        },
        ensure_ascii=False,
        default=str,
    )

    assert "Ruby Devi" not in serialized_provider_data
    assert "+91 9876543210" not in serialized_provider_data
    assert "JOB-1001" not in serialized_provider_data

    # Finally runs even after provider exceptions.
    assert (
        sanitizer.last_placeholder_map
        is not None
    )

    assert len(
        sanitizer.last_placeholder_map
    ) == 0