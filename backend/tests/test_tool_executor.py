import pytest

from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry
from app.tools.examples import generate_sms_schema


def create_executor():
    registry = ToolRegistry()

    @registry.tool(
        schema=generate_sms_schema(),
        category="communication",
        capabilities={"sms"},
    )
    def generate_sms(message: str, priority: str = "normal"):
        return f"{priority}: {message}"

    return ToolExecutor(registry=registry)


def test_execute_registered_tool():
    executor = create_executor()

    result = executor.execute(
        tool_id="generate_sms",
        parameters={"message": "Hello"},
        tenant_id="tenant-1",
    )

    assert result == "normal: Hello"


def test_execute_applies_default_parameter():
    executor = create_executor()

    result = executor.execute(
        tool_id="generate_sms",
        parameters={"message": "Hello"},
        tenant_id="tenant-1",
    )

    assert result.startswith("normal:")


def test_execute_uses_provided_parameter():
    executor = create_executor()

    result = executor.execute(
        tool_id="generate_sms",
        parameters={
            "message": "Urgent message",
            "priority": "high",
        },
        tenant_id="tenant-1",
    )

    assert result == "high: Urgent message"


def test_execute_rejects_invalid_input():
    executor = create_executor()

    with pytest.raises(ValueError):
        executor.execute(
            tool_id="generate_sms",
            parameters={"message": 123},
            tenant_id="tenant-1",
        )


def test_execute_rejects_malicious_input():
    executor = create_executor()

    with pytest.raises(ValueError, match="SQL injection"):
        executor.execute(
            tool_id="generate_sms",
            parameters={
                "message": "DROP TABLE users",
            },
            tenant_id="tenant-1",
        )


def test_execute_rejects_unknown_tool():
    executor = create_executor()

    with pytest.raises(
        ValueError,
        match="Tool 'unknown_tool' not found",
    ):
        executor.execute(
            tool_id="unknown_tool",
            parameters={"message": "Hello"},
            tenant_id="tenant-1",
        )


def test_execute_rejects_tool_without_handler():
    registry = ToolRegistry()
    registry.register_tool(generate_sms_schema())

    executor = ToolExecutor(registry=registry)

    with pytest.raises(
        ValueError,
        match="has no executable handler",
    ):
        executor.execute(
            tool_id="generate_sms",
            parameters={"message": "Hello"},
            tenant_id="tenant-1",
        )


def test_execute_sanitizes_html_before_handler():
    executor = create_executor()

    result = executor.execute(
        tool_id="generate_sms",
        parameters={
            "message": "<b>Hello</b>",
        },
        tenant_id="tenant-1",
    )

    assert result == "normal: Hello"


def test_execute_redacts_pii_before_handler():
    executor = create_executor()

    result = executor.execute(
        tool_id="generate_sms",
        parameters={
            "message": "Contact test@example.com",
        },
        tenant_id="tenant-1",
    )

    assert result == "normal: Contact [REDACTED]"
    