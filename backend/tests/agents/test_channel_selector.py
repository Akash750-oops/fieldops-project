from datetime import datetime, timezone

import pytest

from app.services.ai.FieldOpsAI.agents.channel_selector import (
    ChannelPriority,
    ChannelSelector,
)


@pytest.fixture
def selector():
    return ChannelSelector()


def test_urgency_score_explicit_value(selector):
    assert selector.score_urgency({"urgency_score": 5}) == 5


def test_urgency_score_is_clamped(selector):
    assert selector.score_urgency({"urgency_score": 10}) == 5
    assert selector.score_urgency({"urgency_score": 0}) == 1


def test_urgency_score_invalid_value_defaults_to_three(selector):
    assert selector.score_urgency({"urgency_score": "invalid"}) == 3


@pytest.mark.parametrize(
    ("notification_type", "expected"),
    [
        ("ETA", 5),
        ("ETA_ALERT", 5),
        ("EMERGENCY", 5),
        ("CRITICAL", 5),
        ("URGENT", 4),
        ("JOB_DELAY", 4),
        ("DELAY", 4),
        ("STATUS_UPDATE", 3),
        ("JOB_STATUS", 3),
        ("ENROUTE", 3),
        ("ONSITE", 3),
        ("COMPLETED", 3),
        ("REMINDER", 2),
        ("FOLLOW_UP", 2),
        ("UNKNOWN", 1),
    ],
)
def test_urgency_score_by_notification_type(
    selector,
    notification_type,
    expected,
):
    assert (
        selector.score_urgency(
            {"notification_type": notification_type}
        )
        == expected
    )


def test_quiet_hours_at_10pm(selector):
    current_time = datetime(
        2026,
        8,
        19,
        22,
        0,
        tzinfo=timezone.utc,
    )

    assert selector.is_quiet_hours(
        current_time,
        "UTC",
    ) is True


def test_quiet_hours_before_7am(selector):
    current_time = datetime(
        2026,
        8,
        19,
        6,
        59,
        tzinfo=timezone.utc,
    )

    assert selector.is_quiet_hours(
        current_time,
        "UTC",
    ) is True


def test_quiet_hours_at_7am(selector):
    current_time = datetime(
        2026,
        8,
        19,
        7,
        0,
        tzinfo=timezone.utc,
    )

    assert selector.is_quiet_hours(
        current_time,
        "UTC",
    ) is False


def test_quiet_hours_outside_window(selector):
    current_time = datetime(
        2026,
        8,
        19,
        12,
        0,
        tzinfo=timezone.utc,
    )

    assert selector.is_quiet_hours(
        current_time,
        "UTC",
    ) is False


def test_quiet_hours_requires_timezone_aware_datetime(selector):
    current_time = datetime(
        2026,
        8,
        19,
        22,
        0,
    )

    with pytest.raises(ValueError):
        selector.is_quiet_hours(
            current_time,
            "UTC",
        )


def test_quiet_hours_rejects_unknown_timezone(selector):
    current_time = datetime.now(timezone.utc)

    with pytest.raises(ValueError):
        selector.is_quiet_hours(
            current_time,
            "Invalid/Timezone",
        )


def test_preferred_channel_is_used_first(selector):
    context = {
        "notification_type": "STATUS_UPDATE",
        "current_time": datetime(
            2026,
            8,
            19,
            12,
            0,
            tzinfo=timezone.utc,
        ),
        "timezone": "UTC",
    }

    prefs = {
        "preferred_channel": "EMAIL",
        "email_enabled": True,
    }

    result = selector.select_channel(
        context,
        prefs,
    )

    assert result.channel == "EMAIL"
    assert result.priority == ChannelPriority.PRIMARY
    assert result.urgency_score == 3


def test_in_app_preference_is_normalized_to_portal(selector):
    context = {
        "notification_type": "STATUS_UPDATE",
        "current_time": datetime(
            2026,
            8,
            19,
            12,
            0,
            tzinfo=timezone.utc,
        ),
        "timezone": "UTC",
    }

    prefs = {
        "preferred_channel": "IN_APP",
        "portal_enabled": True,
    }

    result = selector.select_channel(
        context,
        prefs,
    )

    assert result.channel == "PORTAL"


def test_urgent_message_prefers_sms(selector):
    context = {
        "notification_type": "ETA_ALERT",
        "current_time": datetime(
            2026,
            8,
            19,
            12,
            0,
            tzinfo=timezone.utc,
        ),
        "timezone": "UTC",
    }

    prefs = {
        "sms_enabled": True,
    }

    result = selector.select_channel(
        context,
        prefs,
    )

    assert result.channel == "SMS"
    assert result.urgency_score == 5
    assert result.priority == ChannelPriority.PRIMARY


def test_opted_out_sms_is_skipped(selector):
    context = {
        "notification_type": "ETA_ALERT",
        "current_time": datetime(
            2026,
            8,
            19,
            12,
            0,
            tzinfo=timezone.utc,
        ),
        "timezone": "UTC",
    }

    prefs = {
        "sms_enabled": False,
        "push_enabled": True,
    }

    result = selector.select_channel(
        context,
        prefs,
    )

    assert result.channel == "PUSH"
    assert "SMS" in result.attempted_channels


def test_unhealthy_sms_is_skipped(selector):
    def health_checker(channel):
        return channel != "SMS"

    selector = ChannelSelector(
        health_checker=health_checker,
    )

    context = {
        "notification_type": "ETA_ALERT",
        "current_time": datetime(
            2026,
            8,
            19,
            12,
            0,
            tzinfo=timezone.utc,
        ),
        "timezone": "UTC",
    }

    prefs = {
        "sms_enabled": True,
        "push_enabled": True,
    }

    result = selector.select_channel(
        context,
        prefs,
    )

    assert result.channel == "PUSH"
    assert "SMS" in result.attempted_channels


def test_health_checker_exception_marks_channel_unhealthy(selector):
    def health_checker(channel):
        raise RuntimeError("health check failed")

    selector = ChannelSelector(
        health_checker=health_checker,
    )

    assert selector._channel_healthy("SMS") is False


def test_configuration_can_block_sms(selector):
    class ConfigurationService:
        def evaluate_delivery(self, channel, category):
            class Decision:
                allowed = False

            return Decision()

    selector = ChannelSelector(
        configuration_service=ConfigurationService(),
    )

    assert selector._channel_configured(
        "SMS",
        5,
    ) is False


def test_configuration_is_checked_for_sms_and_email(selector):
    calls = []

    class ConfigurationService:
        def evaluate_delivery(self, channel, category):
            calls.append((channel, category))

            class Decision:
                allowed = True

            return Decision()

    selector = ChannelSelector(
        configuration_service=ConfigurationService(),
    )

    assert selector._channel_configured("SMS", 5) is True
    assert selector._channel_configured("EMAIL", 3) is True

    assert len(calls) == 2


def test_push_and_portal_do_not_require_configuration_service(selector):
    assert selector._channel_configured("PUSH", 3) is True
    assert selector._channel_configured("PORTAL", 3) is True


def test_configuration_exception_fails_closed(selector):
    class ConfigurationService:
        def evaluate_delivery(self, channel, category):
            raise RuntimeError("configuration unavailable")

    selector = ChannelSelector(
        configuration_service=ConfigurationService(),
    )

    assert selector._channel_configured("SMS", 3) is False


def test_sms_is_deferred_during_quiet_hours(selector):
    context = {
        "notification_type": "STATUS_UPDATE",
        "current_time": datetime(
            2026,
            8,
            19,
            23,
            0,
            tzinfo=timezone.utc,
        ),
        "timezone": "UTC",
    }

    prefs = {
        "preferred_channel": "SMS",
        "sms_enabled": True,
        "push_enabled": True,
    }

    result = selector.select_channel(
        context,
        prefs,
    )

    assert result.channel == "PUSH"
    assert result.urgency_score == 3


def test_urgent_sms_bypasses_quiet_hours(selector):
    context = {
        "notification_type": "ETA_ALERT",
        "current_time": datetime(
            2026,
            8,
            19,
            23,
            0,
            tzinfo=timezone.utc,
        ),
        "timezone": "UTC",
    }

    prefs = {
        "preferred_channel": "SMS",
        "sms_enabled": True,
    }

    result = selector.select_channel(
        context,
        prefs,
    )

    assert result.channel == "SMS"
    assert result.urgency_score == 5


def test_timezone_aware_quiet_hours(selector):
    # 03:00 UTC = 22:00 previous day in America/New_York.
    current_time = datetime(
        2026,
        8,
        19,
        3,
        0,
        tzinfo=timezone.utc,
    )

    assert selector.is_quiet_hours(
        current_time,
        "America/New_York",
    ) is True


def test_fallback_chain_uses_secondary_channel(selector):
    context = {
        "notification_type": "ETA_ALERT",
        "current_time": datetime(
            2026,
            8,
            19,
            12,
            0,
            tzinfo=timezone.utc,
        ),
        "timezone": "UTC",
    }

    prefs = {
        "preferred_channel": "SMS",
        "sms_enabled": False,
        "push_enabled": True,
    }

    result = selector.select_channel(
        context,
        prefs,
    )

    assert result.channel == "PUSH"
    assert result.priority == ChannelPriority.SECONDARY


def test_fallback_chain_uses_fallback_channel(selector):
    context = {
        "notification_type": "ETA_ALERT",
        "current_time": datetime(
            2026,
            8,
            19,
            12,
            0,
            tzinfo=timezone.utc,
        ),
        "timezone": "UTC",
    }

    prefs = {
        "preferred_channel": "SMS",
        "sms_enabled": False,
        "push_enabled": False,
        "email_enabled": True,
    }

    result = selector.select_channel(
        context,
        prefs,
    )

    assert result.channel == "EMAIL"
    assert result.priority == ChannelPriority.FALLBACK


def test_no_available_channel_returns_none(selector):
    context = {
        "notification_type": "ETA_ALERT",
        "current_time": datetime(
            2026,
            8,
            19,
            12,
            0,
            tzinfo=timezone.utc,
        ),
        "timezone": "UTC",
    }

    prefs = {
        "preferred_channel": "SMS",
        "sms_enabled": False,
        "push_enabled": False,
        "email_enabled": False,
        "portal_enabled": False,
    }

    result = selector.select_channel(
        context,
        prefs,
    )

    assert result.channel is None
    assert result.priority is None


def test_invalid_current_time_type(selector):
    context = {
        "notification_type": "STATUS_UPDATE",
        "current_time": "23:00",
        "timezone": "UTC",
    }

    with pytest.raises(ValueError):
        selector.select_channel(
            context,
            {},
        )


def test_health_checker_false_skips_channel(selector):
    selector = ChannelSelector(
        health_checker=lambda channel: False,
    )

    assert selector._channel_healthy("SMS") is False


def test_preference_service_is_used_for_customer_preference():
    class Decision:
        allowed = False

    class PreferenceService:
        def __init__(self):
            self.calls = []

        def evaluate_channel(
            self,
            tenant_id,
            customer_id,
            channel,
        ):
            self.calls.append(
                (tenant_id, customer_id, channel)
            )
            return Decision()

    preference_service = PreferenceService()

    selector = ChannelSelector(
        preference_service=preference_service,
    )

    prefs = {
        "tenant_id": "tenant-001",
        "customer_id": "customer-001",
    }

    assert selector._channel_allowed(
        "SMS",
        prefs,
    ) is False

    assert preference_service.calls == [
        ("tenant-001", "customer-001", "SMS")
    ]


def test_preference_service_exception_is_not_silently_ignored():
    class PreferenceService:
        def evaluate_channel(
            self,
            tenant_id,
            customer_id,
            channel,
        ):
            raise RuntimeError("preference service failed")

    selector = ChannelSelector(
        preference_service=PreferenceService(),
    )

    with pytest.raises(RuntimeError):
        selector._channel_allowed(
            "SMS",
            {
                "tenant_id": "tenant-001",
                "customer_id": "customer-001",
            },
        )


def test_channel_order_for_urgent_message(selector):
    assert selector._candidate_channels(
        preferred_channel=None,
        urgency_score=5,
    ) == [
        "SMS",
        "PUSH",
        "EMAIL",
        "PORTAL",
    ]


def test_channel_order_for_normal_message(selector):
    assert selector._candidate_channels(
        preferred_channel=None,
        urgency_score=3,
    ) == [
        "PUSH",
        "EMAIL",
        "SMS",
        "PORTAL",
    ]


def test_preferred_channel_moves_to_primary_position(selector):
    result = selector._candidate_channels(
        preferred_channel="EMAIL",
        urgency_score=5,
    )

    assert result[0] == "EMAIL"
    assert "EMAIL" not in result[1:]
    
def test_invalid_preferred_channel_returns_none(selector):
    result = selector._preferred_channel(
        {"preferred_channel": "WHATSAPP"}
    )

    assert result is None
    
    
def test_missing_current_time_uses_utc_now(selector):
    result = selector.select_channel(
        {
            "notification_type": "STATUS_UPDATE",
            "timezone": "UTC",
        },
        {
            "preferred_channel": "EMAIL",
            "email_enabled": True,
        },
    )

    assert result.channel == "EMAIL"
    
    
def test_configuration_blocked_channel_is_skipped(selector):
    class ConfigurationService:
        def evaluate_delivery(self, channel, category):
            class Decision:
                allowed = channel != "SMS"

            return Decision()

    selector = ChannelSelector(
        configuration_service=ConfigurationService(),
    )

    result = selector.select_channel(
        {
            "notification_type": "STATUS_UPDATE",
            "timezone": "UTC",
            "current_time": datetime(
                2026,
                8,
                19,
                12,
                0,
                tzinfo=timezone.utc,
            ),
        },
        {
            "preferred_channel": "SMS",
            "sms_enabled": True,
            "email_enabled": True,
            "push_enabled": False,
            "portal_enabled": False,
        },
    )

    assert result.channel == "EMAIL"
    
def test_non_sms_email_channel_skips_configuration_check(selector):
    class ConfigurationService:
        def evaluate_delivery(self, channel, category):
            raise AssertionError(
                "Configuration service should not be called for PUSH."
            )

    selector = ChannelSelector(
        configuration_service=ConfigurationService(),
    )

    assert selector._channel_configured("PUSH", 3) is True