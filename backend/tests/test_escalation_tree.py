from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from app.services.ai.FieldOpsAI.agents.escalation_tree import (
    EscalationContext,
    EscalationDecisionTree,
    EscalationLevel,
    EscalationTarget,
)


NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("overrides", "trigger", "level", "target"),
    [
        ({"message": "I want a human"}, "EXPLICIT_HUMAN_REQUEST", EscalationLevel.HIGH, EscalationTarget.HUMAN_OPERATOR),
        ({"message": "This is bad", "sentiment": " negative "}, "NEGATIVE_SENTIMENT", EscalationLevel.MEDIUM, EscalationTarget.SENTIMENT_AGENT),
        ({"message": "Please help", "intent": "complaint"}, "COMPLAINT_INTENT", EscalationLevel.HIGH, EscalationTarget.HUMAN_OPERATOR),
        ({"message": "This is poor service"}, "COMPLAINT_CONTENT", EscalationLevel.HIGH, EscalationTarget.HUMAN_OPERATOR),
        ({"message": "Please help", "customer_is_vip": True}, "VIP_CUSTOMER", EscalationLevel.HIGH, EscalationTarget.HUMAN_OPERATOR),
        ({"message": "Please help", "messages_last_hour": 3}, "REPEATED_MESSAGES", EscalationLevel.MEDIUM, EscalationTarget.HUMAN_OPERATOR),
        ({"message": "Please help", "urgent_job": True}, "URGENT_JOB", EscalationLevel.HIGH, EscalationTarget.DISPATCH_AGENT),
        ({"message": "Please help", "sentiment_requires_human": True}, "SENTIMENT_REQUIRES_HUMAN", EscalationLevel.HIGH, EscalationTarget.HUMAN_OPERATOR),
    ],
)
def test_trigger_priority_and_routing(overrides, trigger, level, target):
    decision = EscalationDecisionTree(clock=lambda: NOW).evaluate(
        EscalationContext(**overrides)
    )

    assert decision.should_escalate is True
    assert trigger in decision.triggers
    assert decision.level is level
    assert decision.target is target
    assert decision.sla_minutes == {
        EscalationLevel.CRITICAL: 5,
        EscalationLevel.HIGH: 15,
        EscalationLevel.MEDIUM: 60,
        EscalationLevel.LOW: 240,
    }[level]
    assert decision.sla_deadline == NOW + timedelta(minutes=decision.sla_minutes)
    assert decision.acknowledgement
    expected_eta = (
        f"{decision.sla_minutes} minutes"
        if decision.sla_minutes < 60
        else f"{decision.sla_minutes // 60} hour"
        + ("s" if decision.sla_minutes // 60 != 1 else "")
    )
    assert expected_eta in decision.acknowledgement


def test_critical_explicit_request_for_urgent_job():
    decision = EscalationDecisionTree(clock=lambda: NOW).evaluate(
        EscalationContext(message="I need a human now", urgent_job=True)
    )

    assert decision.level is EscalationLevel.CRITICAL
    assert decision.target is EscalationTarget.HUMAN_OPERATOR
    assert decision.sla_minutes == 5


def test_history_redis_audit_and_sla_timer_are_used():
    redis_client = Mock()
    redis_client.get.return_value = '{"messages_last_hour_threshold": 2}'
    audit_logger = Mock()
    sla_timer = Mock()
    tree = EscalationDecisionTree(
        redis_client=redis_client,
        customer_history_provider=lambda customer_id: {
            "customer_is_vip": True,
            "messages_last_hour": 2,
        },
        audit_logger=audit_logger,
        sla_timer=sla_timer,
        clock=lambda: NOW,
    )

    decision = tree.evaluate(
        EscalationContext(message="Please help", customer_id="customer-1")
    )

    assert "VIP_CUSTOMER" in decision.triggers
    assert "REPEATED_MESSAGES" in decision.triggers
    audit_logger.assert_called_once()
    assert audit_logger.call_args.args[0].target is EscalationTarget.HUMAN_OPERATOR
    sla_timer.assert_called_once_with(decision)
    redis_client.get.assert_called_once_with("fieldops:escalation:rules")


def test_no_trigger_has_no_ack_or_sla():
    decision = EscalationDecisionTree(clock=lambda: NOW).evaluate(
        EscalationContext(message="What time is my appointment?")
    )

    assert decision.should_escalate is False
    assert decision.level is EscalationLevel.LOW
    assert decision.target is EscalationTarget.NONE
    assert decision.sla_minutes is None
    assert decision.acknowledgement is None


def test_communication_agent_delegates_escalation():
    from app.services.ai.FieldOpsAI.agents.communication_agent import CommunicationAgent
    from app.services.ai.FieldOpsAI.schemas.agent_config import AgentConfig
    from app.services.ai.FieldOpsAI.schemas.ai_task import AITask

    tree = Mock()
    expected = object()
    tree.evaluate.return_value = expected
    agent = CommunicationAgent(
        config=AgentConfig(agent_type=AITask.COMMUNICATION, tenant_id="tenant-1"),
        escalation_tree=tree,
    )

    result = agent.evaluate_escalation({"message": "I want a human"})

    assert result is expected
    tree.evaluate.assert_called_once()
    assert tree.evaluate.call_args.args[0].message == "I want a human"


def test_history_lookup_handles_empty_and_failed_providers():
    context = EscalationContext(message="Help", customer_id="customer-1")
    assert EscalationDecisionTree(
        customer_history_provider=lambda _: {},
    )._enrich_context(context) == context
    assert EscalationDecisionTree(
        customer_history_provider=lambda _: (_ for _ in ()).throw(RuntimeError()),
    )._enrich_context(context) == context


def test_history_does_not_override_explicit_values():
    context = EscalationContext(
        message="Help",
        customer_id="customer-1",
        customer_is_vip=True,
        messages_last_hour=4,
    )
    result = EscalationDecisionTree(
        customer_history_provider=lambda _: {
            "customer_is_vip": False,
            "messages_last_hour": 1,
        },
    )._enrich_context(context)
    assert result == context


def test_invalid_cached_rules_fail_open_and_invalid_threshold_uses_default():
    redis_client = Mock()
    redis_client.get.side_effect = RuntimeError()
    tree = EscalationDecisionTree(redis_client=redis_client)
    assert tree._cached_rule("missing", 3) == 3
    assert tree._repeated_message_threshold() == 3

    redis_client.get.side_effect = None
    redis_client.get.return_value = '{"messages_last_hour_threshold": "invalid"}'
    assert tree._repeated_message_threshold() == 3


def test_priority_and_route_fallbacks_and_critical_sentiment():
    tree = EscalationDecisionTree()
    context = EscalationContext(message="Help")
    assert tree._calculate_priority(context=context, triggers=["UNKNOWN"]) is EscalationLevel.LOW
    assert tree._calculate_priority(
        context=context,
        triggers=["ONE", "TWO", "THREE"],
    ) is EscalationLevel.HIGH
    assert tree._route(
        context=context,
        triggers=["UNKNOWN"],
        level=EscalationLevel.LOW,
    ) is EscalationTarget.HUMAN_OPERATOR
    decision = tree.evaluate(
        EscalationContext(
            message="Help",
            sentiment_urgency=EscalationLevel.CRITICAL,
        )
    )
    assert decision.level is EscalationLevel.CRITICAL
