from unittest.mock import MagicMock
import pytest
from app.services.ai.FieldOpsAI.services.realtime_sentiment import (
    RealTimeSentimentScorer,
)


def test_realtime_sentiment_scorer():
    db = MagicMock()

    scorer = RealTimeSentimentScorer(db=db)

    scorer._get_tenant_id = MagicMock(
        return_value="test-tenant"
    )

    result = scorer.score_reply(
        reply_text="Thank you, the technician fixed my issue. Great service!",
        customer_id="customer-1",
        job_id=1,
        channel="SMS",
        language="en",
        context=[],
    )

    assert result is not None
    assert result.sentiment is not None
    assert 0.0 <= result.confidence <= 1.0

    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()

def test_previous_three_messages_are_used():
    db = MagicMock()

    scorer = RealTimeSentimentScorer(db=db)

    # Simulate database result in DESC order:
    # newest message first.
    stored_messages = [
        MagicMock(message="Message 4"),
        MagicMock(message="Message 3"),
        MagicMock(message="Message 2"),
    ]

    (
        db.query.return_value
        .filter.return_value
        .order_by.return_value
        .limit.return_value
        .all.return_value
    ) = stored_messages

    messages = scorer._get_previous_messages(
        customer_id="customer-1",
        job_id=1,
    )

    assert messages == [
        "Message 2",
        "Message 3",
        "Message 4",
    ]

    db.query.return_value.filter.return_value.order_by.return_value.limit.assert_called_once_with(3)

def test_automated_reply_is_skipped():
    db = MagicMock()

    scorer = RealTimeSentimentScorer(db=db)

    result = scorer.score_reply(
        reply_text="Automatic reply: I am currently out of office.",
        customer_id="customer-1",
        job_id=1,
        channel="SMS",
        language="en",
        context=[],
    )

    assert result is None

    db.add.assert_not_called()
    db.commit.assert_not_called()

def test_negative_high_confidence_triggers_alert():
    db = MagicMock()

    scorer = RealTimeSentimentScorer(db=db)

    negative_result = MagicMock(
        sentiment="NEGATIVE",
        confidence=0.95,
    )

    assert scorer._should_alert_negative(
        negative_result
    ) is True

def test_negative_low_confidence_does_not_trigger_alert():
    db = MagicMock()

    scorer = RealTimeSentimentScorer(db=db)

    negative_result = MagicMock(
        sentiment="NEGATIVE",
        confidence=0.75,
    )

    assert scorer._should_alert_negative(
        negative_result
    ) is False


def test_negative_sentiment_creates_alert():
    db = MagicMock()

    scorer = RealTimeSentimentScorer(db=db)

    job = MagicMock()
    job.id = 1
    job.tenant_id = "tenant-1"
    job.attempt_count = 0

    db.query.return_value.filter.return_value.first.return_value = job

    negative_result = MagicMock(
        sentiment="NEGATIVE",
        confidence=0.95,
    )

    scorer.sentiment_integration.analyze = MagicMock(
        return_value=negative_result
    )

    scorer.score_reply(
        reply_text="This service was terrible.",
        customer_id="customer-1",
        job_id=1,
        channel="SMS",
        language="en",
        context=[],
    )

    assert db.add.called
    assert db.commit.called

def test_positive_to_negative_sentiment_shift():
    db = MagicMock()

    scorer = RealTimeSentimentScorer(db=db)

    previous_result = MagicMock(
        sentiment="POSITIVE",
        confidence=0.95,
    )

    scorer.sentiment_integration.analyze = MagicMock(
        return_value=previous_result
    )

    result = scorer._has_sentiment_shift(
        previous_messages=[
            "Thank you, the service was excellent."
        ],
        current_sentiment="NEGATIVE",
    )

    assert result is True

def test_no_shift_when_current_sentiment_is_positive():
    db = MagicMock()

    scorer = RealTimeSentimentScorer(db=db)

    result = scorer._has_sentiment_shift(
        previous_messages=[
            "Thank you, the service was excellent."
        ],
        current_sentiment="POSITIVE",
    )

    assert result is False


def test_negative_sentiment_triggers_alert():
    db = MagicMock()

    scorer = RealTimeSentimentScorer(db=db)

    job = MagicMock()
    job.id = 1
    job.tenant_id = "tenant-1"
    job.attempt_count = 0

    db.query.return_value.filter.return_value.first.return_value = job

    negative_result = MagicMock(
        sentiment="NEGATIVE",
        confidence=0.95,
    )

    scorer.sentiment_integration.analyze = MagicMock(
        return_value=negative_result
    )

    scorer.score_reply(
        reply_text="This service was terrible.",
        customer_id="customer-1",
        job_id=1,
        channel="SMS",
        language="en",
        context=[],
    )

    assert db.add.called
    assert db.commit.called


def test_supported_sentiment_channels():
    db = MagicMock()

    scorer = RealTimeSentimentScorer(db=db)

    result = MagicMock(
        sentiment="POSITIVE",
        confidence=0.95,
    )

    scorer.sentiment_integration.analyze = MagicMock(
        return_value=result
    )

    for channel in ["SMS", "EMAIL", "PORTAL"]:
        response = scorer.score_reply(
            reply_text="Thank you for the great service.",
            customer_id="customer-1",
            job_id=1,
            channel=channel,
            language="en",
            context=[],
        )

        assert response is not None

    assert scorer.sentiment_integration.analyze.call_count == 3


def test_job_sentiment_summary():
    db = MagicMock()

    scorer = RealTimeSentimentScorer(db=db)

    records = [
        MagicMock(sentiment="POSITIVE"),
        MagicMock(sentiment="NEUTRAL"),
        MagicMock(sentiment="NEGATIVE"),
    ]

    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = records

    summary = scorer.get_job_sentiment_summary(job_id=1)

    assert summary["job_id"] == 1
    assert summary["average_score"] == 0.0
    assert summary["trend"] == "DECLINING"


def test_job_sentiment_trend_improving():
    db = MagicMock()
    scorer = RealTimeSentimentScorer(db=db)

    records = [
        MagicMock(sentiment="NEGATIVE"),
        MagicMock(sentiment="POSITIVE"),
    ]

    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = records

    summary = scorer.get_job_sentiment_summary(job_id=1)

    assert summary["trend"] == "IMPROVING"


def test_job_sentiment_trend_stable():
    db = MagicMock()
    scorer = RealTimeSentimentScorer(db=db)

    records = [
        MagicMock(sentiment="POSITIVE"),
        MagicMock(sentiment="POSITIVE"),
    ]

    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = records

    summary = scorer.get_job_sentiment_summary(job_id=1)

    assert summary["trend"] == "STABLE"

def test_job_sentiment_summary_empty():
    db = MagicMock()
    scorer = RealTimeSentimentScorer(db=db)

    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

    summary = scorer.get_job_sentiment_summary(job_id=1)

    assert summary["job_id"] == 1
    assert summary["average_score"] == 0.0
    assert summary["trend"] == "NEUTRAL"


def test_automated_replies_are_skipped():
    db = MagicMock()
    scorer = RealTimeSentimentScorer(db=db)

    analyze_mock = MagicMock()
    scorer.sentiment_integration.analyze = analyze_mock

    automated_messages = [
        "Out of office until Monday.",
        "This is an automatic reply.",
        "Mail delivery failed.",
        "Message could not be delivered.",
    ]

    for message in automated_messages:
        result = scorer.score_reply(
            reply_text=message,
            customer_id="customer-1",
            job_id=1,
            channel="EMAIL",
            language="en",
            context=[],
        )

        assert result is None

    analyze_mock.assert_not_called()

def test_unsupported_sentiment_channel_rejected():
    db = MagicMock()
    scorer = RealTimeSentimentScorer(db=db)

    with pytest.raises(ValueError, match="Unsupported sentiment channel"):
        scorer.score_reply(
            reply_text="I need help with my service.",
            customer_id="customer-1",
            job_id=1,
            channel="WHATSAPP",
            language="en",
            context=[],
        )


def test_negative_confidence_at_threshold_does_not_trigger_alert():
    db = MagicMock()
    scorer = RealTimeSentimentScorer(db=db)

    result = MagicMock(
        sentiment="NEGATIVE",
        confidence=0.8,
    )

    assert scorer._should_alert_negative(result) is False


def test_empty_reply_is_skipped():
    db = MagicMock()
    scorer = RealTimeSentimentScorer(db=db)

    analyze_mock = MagicMock()
    scorer.sentiment_integration.analyze = analyze_mock

    for message in ["", "   ", "\n\t"]:
        result = scorer.score_reply(
            reply_text=message,
            customer_id="customer-1",
            job_id=1,
            channel="SMS",
            language="en",
            context=[],
        )

        assert result is None

    analyze_mock.assert_not_called()

def test_job_sentiment_summary_single_message():
    db = MagicMock()
    scorer = RealTimeSentimentScorer(db=db)

    records = [
        MagicMock(sentiment="NEGATIVE"),
    ]

    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = records

    summary = scorer.get_job_sentiment_summary(job_id=1)

    assert summary["job_id"] == 1
    assert summary["average_score"] == -1.0
    assert summary["trend"] == "NEUTRAL"


def test_job_sentiment_average_score():
    db = MagicMock()
    scorer = RealTimeSentimentScorer(db=db)

    records = [
        MagicMock(sentiment="POSITIVE"),
        MagicMock(sentiment="MIXED"),
        MagicMock(sentiment="NEGATIVE"),
    ]

    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = records

    summary = scorer.get_job_sentiment_summary(job_id=1)

    # (1.0 + 0.5 - 1.0) / 3 = 0.1667
    assert summary["average_score"] == 0.167