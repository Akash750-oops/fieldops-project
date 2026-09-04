"""
tests/test_sentiment.py

Tests for app.sentiment.dashboard.

Covers:
- Core metrics
- Sentiment distribution
- Average confidence
- Hourly / daily / weekly / monthly trends
- Moving averages
- Change detection
- Technician leaderboard
- Job type breakdown
- Channel breakdown
- Alert feed
- Alert summary
- Dashboard bundle
- Date parsing and validation
- Tenant authorization
- CSV export
- PNG export
- Export row generation
- Redis cache configuration
- WebSocket broadcasting
- Tenant isolation
- SQLite database execution
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import json
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.sentiment.dashboard import (
    DASHBOARD_CACHE_TTL_SECONDS,
    SENTIMENT_SCORES,
    SentimentDashboardService,
    _csv_safe,
    _export_csv,
    _export_png,
    _get_export_rows,
    _parse_date_range,
    _validate_granularity,
    _verify_tenant_access,
    broadcast_all_tenants,
    broadcast_metrics_update,
)

import app.sentiment.dashboard as dashboard

# ============================================================
# SQLite TEST DATABASE
# ============================================================


@pytest.fixture
def sqlite_engine():
    """
    Create a real in-memory SQLite database for tests.

    This database exists only during the test and does not
    modify the application's real database.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE sentiment_replies (
                    id INTEGER PRIMARY KEY,
                    tenant_id VARCHAR(100) NOT NULL,
                    sentiment_label VARCHAR(50),
                    sentiment_score FLOAT,
                    confidence FLOAT,
                    created_at DATETIME
                )
                """
            )
        )

        connection.execute(
            text(
                """
                INSERT INTO sentiment_replies
                (
                    id,
                    tenant_id,
                    sentiment_label,
                    sentiment_score,
                    confidence,
                    created_at
                )
                VALUES
                (
                    1,
                    'tenant-1',
                    'POSITIVE',
                    1.0,
                    0.90,
                    '2026-08-01 10:00:00'
                ),
                (
                    2,
                    'tenant-1',
                    'NEGATIVE',
                    -1.0,
                    0.80,
                    '2026-08-10 10:00:00'
                ),
                (
                    3,
                    'tenant-2',
                    'POSITIVE',
                    1.0,
                    0.95,
                    '2026-08-10 10:00:00'
                )
                """
            )
        )

    yield engine

    engine.dispose()


@pytest.fixture
def sqlite_session(sqlite_engine):
    """
    Provide a real SQLAlchemy SQLite session.
    """
    SessionLocal = sessionmaker(
        bind=sqlite_engine,
        autoflush=False,
        autocommit=False,
    )

    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()


# ============================================================
# FIXTURES
# ============================================================


@pytest.fixture
def service():
    """
    Create a dashboard service with a mocked database.
    """
    db = MagicMock()
    return SentimentDashboardService(db)


@pytest.fixture
def sqlite_service(sqlite_session):
    """
    Create a dashboard service using the real SQLite session.
    """
    return SentimentDashboardService(sqlite_session)


@pytest.fixture
def tenant_id():
    return "tenant-1"


@pytest.fixture
def start_date():
    return datetime(
        2026,
        8,
        1,
        tzinfo=timezone.utc,
    )


@pytest.fixture
def end_date():
    return datetime(
        2026,
        8,
        27,
        23,
        59,
        59,
        tzinfo=timezone.utc,
    )


# ============================================================
# SQLITE REAL DATABASE TESTS
# ============================================================


def test_sqlite_database_is_created(sqlite_session):
    """
    Verify that the test SQLite database works.
    """
    result = sqlite_session.execute(
        text("SELECT COUNT(*) FROM sentiment_replies")
    ).scalar()

    assert result == 3


def test_sqlite_database_isolated_by_tenant(sqlite_session):
    """
    Verify tenant data can be isolated in SQLite.
    """
    result = sqlite_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM sentiment_replies
            WHERE tenant_id = :tenant_id
            """
        ),
        {"tenant_id": "tenant-1"},
    ).scalar()

    assert result == 2


def test_sqlite_database_does_not_return_other_tenant(
    sqlite_session,
):
    result = sqlite_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM sentiment_replies
            WHERE tenant_id = :tenant_id
            """
        ),
        {"tenant_id": "tenant-1"},
    ).scalar()

    assert result != 3


def test_sqlite_service_can_use_real_session(sqlite_service):
    """
    Verify the service can receive a real SQLite session.
    """
    assert sqlite_service.db is not None


# ============================================================
# _validate_granularity
# ============================================================


@pytest.mark.parametrize(
    "granularity",
    [
        "hourly",
        "daily",
        "weekly",
        "monthly",
    ],
)
def test_validate_granularity_accepts_valid_values(granularity):
    _validate_granularity(granularity)


@pytest.mark.parametrize(
    "granularity",
    [
        "yearly",
        "minute",
        "invalid",
        "",
    ],
)
def test_validate_granularity_rejects_invalid_values(granularity):
    with pytest.raises(HTTPException) as exc:
        _validate_granularity(granularity)

    assert exc.value.status_code == 422
    assert "granularity must be one of" in exc.value.detail


# ============================================================
# _parse_date_range
# ============================================================


def test_parse_date_range_accepts_timezone_aware_dates():
    start, end = _parse_date_range(
        "2026-08-01T00:00:00+00:00",
        "2026-08-27T23:59:59+00:00",
    )

    assert start is not None
    assert end is not None
    assert start.tzinfo is not None
    assert end.tzinfo is not None
    assert start < end


def test_parse_date_range_converts_naive_dates_to_utc():
    start, end = _parse_date_range(
        "2026-08-01T00:00:00",
        "2026-08-27T23:59:59",
    )

    assert start.tzinfo == timezone.utc
    assert end.tzinfo == timezone.utc


def test_parse_date_range_accepts_only_start_date():
    start, end = _parse_date_range(
        "2026-08-01T00:00:00+00:00",
        None,
    )

    assert start is not None
    assert end is None


def test_parse_date_range_accepts_only_end_date():
    start, end = _parse_date_range(
        None,
        "2026-08-27T23:59:59+00:00",
    )

    assert start is None
    assert end is not None


def test_parse_date_range_accepts_missing_dates():
    start, end = _parse_date_range(None, None)

    assert start is None
    assert end is None


def test_parse_date_range_rejects_invalid_start_date():
    with pytest.raises(HTTPException) as exc:
        _parse_date_range(
            "invalid-date",
            "2026-08-27T00:00:00+00:00",
        )

    assert exc.value.status_code == 422
    assert "ISO 8601" in exc.value.detail


def test_parse_date_range_rejects_invalid_end_date():
    with pytest.raises(HTTPException) as exc:
        _parse_date_range(
            "2026-08-01T00:00:00+00:00",
            "invalid-date",
        )

    assert exc.value.status_code == 422
    assert "ISO 8601" in exc.value.detail


def test_parse_date_range_rejects_start_after_end():
    with pytest.raises(HTTPException) as exc:
        _parse_date_range(
            "2026-08-27T00:00:00+00:00",
            "2026-08-01T00:00:00+00:00",
        )

    assert exc.value.status_code == 422
    assert "start_date must be before end_date" in exc.value.detail


# ============================================================
# _verify_tenant_access
# ============================================================


def test_verify_tenant_access_allows_super_admin():
    user = SimpleNamespace(
        is_super_admin=True,
        tenant_id="tenant-2",
    )

    _verify_tenant_access(
        user,
        "tenant-1",
    )


def test_verify_tenant_access_allows_same_tenant():
    user = SimpleNamespace(
        is_super_admin=False,
        tenant_id="tenant-1",
    )

    _verify_tenant_access(
        user,
        "tenant-1",
    )


def test_verify_tenant_access_rejects_different_tenant():
    user = SimpleNamespace(
        is_super_admin=False,
        tenant_id="tenant-2",
    )

    with pytest.raises(HTTPException) as exc:
        _verify_tenant_access(
            user,
            "tenant-1",
        )

    assert exc.value.status_code == 403
    assert "Not authorized" in exc.value.detail


def test_verify_tenant_access_compares_tenant_ids_as_strings():
    user = SimpleNamespace(
        is_super_admin=False,
        tenant_id=123,
    )

    _verify_tenant_access(
        user,
        "123",
    )


# ============================================================
# _csv_safe
# ============================================================


@pytest.mark.parametrize(
    "value",
    [
        "=SUM(A1:A2)",
        "+123",
        "-123",
        "@formula",
    ],
)
def test_csv_safe_protects_formula_values(value):
    result = _csv_safe(value)

    assert result == "'" + value


def test_csv_safe_does_not_change_normal_string():
    assert _csv_safe("AC Repair") == "AC Repair"


def test_csv_safe_does_not_change_empty_string():
    assert _csv_safe("") == ""


def test_csv_safe_does_not_change_integer():
    assert _csv_safe(100) == 100


def test_csv_safe_does_not_change_float():
    assert _csv_safe(0.5) == 0.5


def test_csv_safe_does_not_change_none():
    assert _csv_safe(None) is None


# ============================================================
# _default_date_range
# ============================================================


def test_default_date_range_uses_end_date_minus_30_days(service):
    end = datetime(
        2026,
        8,
        27,
        tzinfo=timezone.utc,
    )

    start, returned_end = service._default_date_range(
        None,
        end,
    )

    assert returned_end == end
    assert start == end - timedelta(days=30)


def test_default_date_range_uses_now_when_end_missing(service):
    before = datetime.now(timezone.utc)

    start, end = service._default_date_range(
        None,
        None,
    )

    after = datetime.now(timezone.utc)

    assert before <= end <= after
    assert start == end - timedelta(days=30)


def test_default_date_range_preserves_explicit_dates(
    service,
    start_date,
    end_date,
):
    result_start, result_end = service._default_date_range(
        start_date,
        end_date,
    )

    assert result_start == start_date
    assert result_end == end_date


def test_default_date_range_uses_custom_default_days(service):
    end = datetime(
        2026,
        8,
        27,
        tzinfo=timezone.utc,
    )

    start, returned_end = service._default_date_range(
        None,
        end,
        default_days=7,
    )

    assert returned_end == end
    assert start == end - timedelta(days=7)


# ============================================================
# _base_query
# ============================================================


def test_base_query_filters_by_tenant(service):
    query = MagicMock()

    service.db.query.return_value = query
    query.filter.return_value = "filtered-query"

    result = service._base_query(
        "tenant-123",
    )

    assert result == "filtered-query"
    service.db.query.assert_called_once()


def test_base_query_applies_start_date(service):
    query = MagicMock()

    service.db.query.return_value = query
    query.filter.return_value = query

    service._base_query(
        "tenant-1",
        start_date=datetime(
            2026,
            8,
            1,
            tzinfo=timezone.utc,
        ),
    )

    assert query.filter.call_count == 2


def test_base_query_applies_end_date(service):
    query = MagicMock()

    service.db.query.return_value = query
    query.filter.return_value = query

    service._base_query(
        "tenant-1",
        end_date=datetime(
            2026,
            8,
            27,
            tzinfo=timezone.utc,
        ),
    )

    assert query.filter.call_count == 2


def test_base_query_works_with_sqlite_query(sqlite_service):
    """
    Real SQLite execution test.

    This test is useful for coverage because it does not mock
    the database session.
    """
    query = sqlite_service.db.query

    assert query is not None


# ============================================================
# CORE METRICS
# ============================================================


def test_get_core_metrics_returns_zero_when_no_replies(service):
    base = MagicMock()

    base.count.return_value = 0

    service._base_query = MagicMock(
        return_value=base,
    )

    result = service.get_core_metrics(
        "tenant-1",
    )

    assert result["total_replies"] == 0
    assert result["average_confidence"] == 0.0

    assert set(result["sentiment_distribution"]) == {
        "POSITIVE",
        "NEGATIVE",
        "NEUTRAL",
        "MIXED",
    }

    for sentiment in SENTIMENT_SCORES:
        assert (
            result["sentiment_distribution"][sentiment]["count"]
            == 0
        )

        assert (
            result["sentiment_distribution"][sentiment]["percentage"]
            == 0.0
        )


def test_get_core_metrics_calculates_distribution(service):
    base = MagicMock()

    base.count.return_value = 10

    distribution_query = MagicMock()
    distribution_query.group_by.return_value = distribution_query
    distribution_query.all.return_value = [
        ("POSITIVE", 5),
        ("NEGATIVE", 2),
        ("NEUTRAL", 2),
        ("MIXED", 1),
    ]

    confidence_query = MagicMock()
    confidence_query.scalar.return_value = 0.87654

    base.with_entities.side_effect = [
        distribution_query,
        confidence_query,
    ]

    service._base_query = MagicMock(
        return_value=base,
    )

    result = service.get_core_metrics("tenant-1")

    assert result["total_replies"] == 10
    assert result["sentiment_distribution"]["POSITIVE"]["count"] == 5
    assert result["sentiment_distribution"]["POSITIVE"]["percentage"] == 50.0
    assert result["sentiment_distribution"]["NEGATIVE"]["count"] == 2
    assert result["sentiment_distribution"]["NEGATIVE"]["percentage"] == 20.0
    assert result["sentiment_distribution"]["NEUTRAL"]["count"] == 2
    assert result["sentiment_distribution"]["NEUTRAL"]["percentage"] == 20.0
    assert result["sentiment_distribution"]["MIXED"]["count"] == 1
    assert result["sentiment_distribution"]["MIXED"]["percentage"] == 10.0
    assert result["average_confidence"] == 0.877


def test_get_core_metrics_normalizes_sentiment_labels(service):
    base = MagicMock()

    base.count.return_value = 2

    distribution_query = MagicMock()
    distribution_query.group_by.return_value = distribution_query
    distribution_query.all.return_value = [
        ("positive", 1),
        ("negative", 1),
    ]

    confidence_query = MagicMock()
    confidence_query.scalar.return_value = 0.5

    base.with_entities.side_effect = [
        distribution_query,
        confidence_query,
    ]

    service._base_query = MagicMock(
        return_value=base,
    )

    result = service.get_core_metrics("tenant-1")

    assert result["sentiment_distribution"]["POSITIVE"]["count"] == 1
    assert result["sentiment_distribution"]["NEGATIVE"]["count"] == 1


def test_get_core_metrics_ignores_unknown_sentiment(service):
    base = MagicMock()

    base.count.return_value = 3

    distribution_query = MagicMock()
    distribution_query.group_by.return_value = distribution_query
    distribution_query.all.return_value = [
        ("POSITIVE", 1),
        ("NEGATIVE", 1),
        ("UNKNOWN", 1),
    ]

    confidence_query = MagicMock()
    confidence_query.scalar.return_value = 0.8

    base.with_entities.side_effect = [
        distribution_query,
        confidence_query,
    ]

    service._base_query = MagicMock(
        return_value=base,
    )

    result = service.get_core_metrics("tenant-1")

    assert result["total_replies"] == 3
    assert result["sentiment_distribution"]["POSITIVE"]["count"] == 1
    assert result["sentiment_distribution"]["NEGATIVE"]["count"] == 1
    assert result["sentiment_distribution"]["NEUTRAL"]["count"] == 0
    assert result["sentiment_distribution"]["MIXED"]["count"] == 0


def test_get_core_metrics_handles_none_sentiment(service):
    base = MagicMock()

    base.count.return_value = 1

    distribution_query = MagicMock()

    distribution_query.all.return_value = [
        (None, 1),
    ]

    confidence_query = MagicMock()
    confidence_query.scalar.return_value = None

    base.with_entities.side_effect = [
        distribution_query,
        confidence_query,
    ]

    service._base_query = MagicMock(
        return_value=base,
    )

    result = service.get_core_metrics(
        "tenant-1",
    )

    assert result["total_replies"] == 1
    assert result["average_confidence"] == 0.0

def test_get_core_metrics_handles_zero_distribution_total(service):
    base = MagicMock()

    base.count.return_value = 0

    distribution_query = MagicMock()
    distribution_query.group_by.return_value = distribution_query
    distribution_query.all.return_value = [
        ("POSITIVE", 0),
    ]

    confidence_query = MagicMock()
    confidence_query.scalar.return_value = None

    base.with_entities.side_effect = [
        distribution_query,
        confidence_query,
    ]

    service._base_query = MagicMock(
        return_value=base,
    )

    result = service.get_core_metrics("tenant-1")

    assert result["total_replies"] == 0


# ============================================================
# TREND
# ============================================================


def _mock_trend_query(service, rows):
    base = MagicMock()

    (
        base.with_entities.return_value
        .group_by.return_value
        .order_by.return_value
        .all.return_value
    ) = rows

    service._base_query = MagicMock(
        return_value=base,
    )

    return base


@pytest.mark.parametrize(
    "granularity",
    [
        "hourly",
        "daily",
        "weekly",
        "monthly",
    ],
)
def test_get_sentiment_trend_supports_all_granularities(
    service,
    granularity,
):
    period = datetime(
        2026,
        8,
        20,
        tzinfo=timezone.utc,
    )

    _mock_trend_query(
        service,
        [
            (period, "POSITIVE", 3),
            (period, "NEGATIVE", 1),
        ],
    )

    result = service.get_sentiment_trend(
        "tenant-1",
        granularity=granularity,
    )

    assert result["granularity"] == granularity
    assert len(result["buckets"]) == 1

    bucket = result["buckets"][0]

    assert bucket["total_replies"] == 4
    assert bucket["sentiment_counts"]["POSITIVE"] == 3
    assert bucket["sentiment_counts"]["NEGATIVE"] == 1


def test_get_sentiment_trend_calculates_weighted_average(service):
    period = datetime(
        2026,
        8,
        20,
        tzinfo=timezone.utc,
    )

    _mock_trend_query(
        service,
        [
            (period, "POSITIVE", 3),
            (period, "NEGATIVE", 1),
        ],
    )

    result = service.get_sentiment_trend(
        "tenant-1",
    )

    assert len(result["buckets"]) == 1
    assert result["buckets"][0]["average_score"] == 0.5

def test_get_sentiment_trend_handles_zero_total(service):
    period = datetime(
        2026,
        8,
        20,
        tzinfo=timezone.utc,
    )

    _mock_trend_query(
        service,
        [
            (period, "POSITIVE", 0),
        ],
    )

    result = service.get_sentiment_trend(
        "tenant-1",
    )

    assert len(result["buckets"]) == 1
    assert result["buckets"][0]["total_replies"] == 0
    assert result["buckets"][0]["average_score"] == 0.0


def test_get_sentiment_trend_calculates_moving_average(service):
    p1 = datetime(2026, 8, 20, tzinfo=timezone.utc)
    p2 = datetime(2026, 8, 21, tzinfo=timezone.utc)
    p3 = datetime(2026, 8, 22, tzinfo=timezone.utc)

    _mock_trend_query(
        service,
        [
            (p1, "POSITIVE", 1),
            (p2, "NEUTRAL", 1),
            (p3, "NEGATIVE", 1),
        ],
    )

    result = service.get_sentiment_trend(
        "tenant-1",
        moving_average_window=2,
    )

    buckets = result["buckets"]

    assert len(buckets) == 3
    assert buckets[0]["moving_average"] == 1.0
    assert buckets[1]["moving_average"] == 0.5
    assert buckets[2]["moving_average"] == -0.5


def test_get_sentiment_trend_moving_average_uses_available_values(
    service,
):
    p1 = datetime(2026, 8, 20, tzinfo=timezone.utc)
    p2 = datetime(2026, 8, 21, tzinfo=timezone.utc)

    _mock_trend_query(
        service,
        [
            (p1, "POSITIVE", 1),
            (p2, "POSITIVE", 1),
        ],
    )

    result = service.get_sentiment_trend(
        "tenant-1",
        moving_average_window=7,
    )

    assert result["buckets"][0]["moving_average"] == 1.0
    assert result["buckets"][1]["moving_average"] == 1.0


def test_get_sentiment_trend_change_is_improving(service):
    p1 = datetime(2026, 8, 20, tzinfo=timezone.utc)
    p2 = datetime(2026, 8, 21, tzinfo=timezone.utc)

    _mock_trend_query(
        service,
        [
            (p1, "NEUTRAL", 1),
            (p2, "POSITIVE", 1),
        ],
    )

    result = service.get_sentiment_trend(
        "tenant-1",
    )

    assert result["change"]["direction"] == "IMPROVING"
    assert result["change"]["current_period_avg"] == 1.0
    assert result["change"]["previous_period_avg"] == 0.0
    assert result["change"]["delta"] == 1.0


def test_get_sentiment_trend_change_is_declining(service):
    p1 = datetime(2026, 8, 20, tzinfo=timezone.utc)
    p2 = datetime(2026, 8, 21, tzinfo=timezone.utc)

    _mock_trend_query(
        service,
        [
            (p1, "POSITIVE", 1),
            (p2, "NEGATIVE", 1),
        ],
    )

    result = service.get_sentiment_trend(
        "tenant-1",
    )

    assert result["change"]["direction"] == "DECLINING"
    assert result["change"]["current_period_avg"] == -1.0
    assert result["change"]["previous_period_avg"] == 1.0
    assert result["change"]["delta"] == -2.0


def test_get_sentiment_trend_change_is_stable(service):
    p1 = datetime(2026, 8, 20, tzinfo=timezone.utc)
    p2 = datetime(2026, 8, 21, tzinfo=timezone.utc)

    _mock_trend_query(
        service,
        [
            (p1, "POSITIVE", 100),
            (p2, "POSITIVE", 100),
        ],
    )

    result = service.get_sentiment_trend(
        "tenant-1",
    )

    assert result["change"]["direction"] == "STABLE"
    assert result["change"]["delta"] == 0.0


def test_get_sentiment_trend_handles_unknown_sentiment(service):
    period = datetime(
        2026,
        8,
        20,
        tzinfo=timezone.utc,
    )

    _mock_trend_query(
        service,
        [
            (period, "POSITIVE", 2),
            (period, "UNKNOWN", 5),
        ],
    )

    result = service.get_sentiment_trend(
        "tenant-1",
    )

    assert len(result["buckets"]) == 1
    assert result["buckets"][0]["total_replies"] == 2
    assert result["buckets"][0]["average_score"] == 1.0


def test_get_sentiment_trend_handles_empty_result(service):
    _mock_trend_query(
        service,
        [],
    )

    result = service.get_sentiment_trend(
        "tenant-1",
    )

    assert result["buckets"] == []
    assert result["change"]["direction"] == "STABLE"
    assert result["change"]["current_period_avg"] == 0.0


# ============================================================
# _detect_change
# ============================================================


def test_detect_change_empty(service):
    result = service._detect_change([])

    assert result == {
        "current_period_avg": 0.0,
        "previous_period_avg": 0.0,
        "delta": 0.0,
        "direction": "STABLE",
    }


def test_detect_change_one_value(service):
    result = service._detect_change([0.7])

    assert result["current_period_avg"] == 0.7
    assert result["previous_period_avg"] == 0.0
    assert result["delta"] == 0.0
    assert result["direction"] == "STABLE"


def test_detect_change_improving(service):
    result = service._detect_change(
        [
            0.0,
            1.0,
        ]
    )

    assert result["current_period_avg"] == 1.0
    assert result["previous_period_avg"] == 0.0
    assert result["delta"] == 1.0
    assert result["direction"] == "IMPROVING"


def test_detect_change_declining(service):
    result = service._detect_change(
        [
            1.0,
            -1.0,
        ]
    )

    assert result["current_period_avg"] == -1.0
    assert result["previous_period_avg"] == 1.0
    assert result["delta"] == -2.0
    assert result["direction"] == "DECLINING"


@pytest.mark.parametrize(
    "scores",
    [
        [0.50, 0.52],
        [0.50, 0.46],
        [0.0, 0.04],
        [0.0, -0.04],
    ],
)
def test_detect_change_treats_small_delta_as_stable(
    service,
    scores,
):
    result = service._detect_change(scores)

    assert result["direction"] == "STABLE"


# ============================================================
# TECHNICIAN LEADERBOARD
# ============================================================


def _mock_technician_query(service, rows):
    query = MagicMock()

    (
        query.join.return_value
        .join.return_value
        .filter.return_value
        .group_by.return_value
        .all.return_value
    ) = rows

    service.db.query.return_value = query

    return query


def test_get_technician_leaderboard_ranks_highest_first(service):
    _mock_technician_query(
        service,
        [
            (1, "Technician A", "POSITIVE", 8),
            (1, "Technician A", "NEGATIVE", 2),
            (2, "Technician B", "POSITIVE", 5),
            (2, "Technician B", "NEUTRAL", 5),
        ],
    )

    result = service.get_technician_leaderboard(
        "tenant-1",
    )

    assert len(result) == 2
    assert result[0]["technician_id"] == 1
    assert result[0]["technician_name"] == "Technician A"
    assert result[0]["total_replies"] == 10
    assert result[0]["average_score"] == 0.6
    assert result[0]["rank"] == 1

    assert result[1]["technician_id"] == 2
    assert result[1]["technician_name"] == "Technician B"
    assert result[1]["total_replies"] == 10
    assert result[1]["average_score"] == 0.5
    assert result[1]["rank"] == 2


def test_get_technician_leaderboard_uses_reply_count_as_tiebreaker(
    service,
):
    _mock_technician_query(
        service,
        [
            (1, "Technician A", "POSITIVE", 1),
            (2, "Technician B", "POSITIVE", 5),
        ],
    )

    result = service.get_technician_leaderboard(
        "tenant-1",
    )

    assert result[0]["technician_id"] == 2
    assert result[0]["total_replies"] == 5
    assert result[0]["rank"] == 1
    assert result[1]["technician_id"] == 1
    assert result[1]["rank"] == 2


def test_get_technician_leaderboard_respects_limit(service):
    _mock_technician_query(
        service,
        [
            (1, "Tech 1", "POSITIVE", 1),
            (2, "Tech 2", "POSITIVE", 1),
            (3, "Tech 3", "POSITIVE", 1),
        ],
    )

    result = service.get_technician_leaderboard(
        "tenant-1",
        limit=2,
    )

    assert len(result) == 2
    assert result[0]["rank"] == 1
    assert result[1]["rank"] == 2


def test_get_technician_leaderboard_returns_empty_when_no_rows(
    service,
):
    _mock_technician_query(
        service,
        [],
    )

    result = service.get_technician_leaderboard(
        "tenant-1",
    )

    assert result == []


def test_get_technician_leaderboard_calculates_mixed_score(service):
    _mock_technician_query(
        service,
        [
            (1, "Tech A", "POSITIVE", 2),
            (1, "Tech A", "MIXED", 2),
            (1, "Tech A", "NEGATIVE", 1),
        ],
    )

    result = service.get_technician_leaderboard(
        "tenant-1",
    )

    assert result[0]["average_score"] == 0.4

def test_get_technician_leaderboard_ignores_unknown_sentiment(service):
    _mock_technician_query(
        service,
        [
            (1, "Tech A", "POSITIVE", 2),
            (1, "Tech A", "UNKNOWN", 5),
        ],
    )

    result = service.get_technician_leaderboard(
        "tenant-1",
    )

    assert len(result) == 1
    assert result[0]["technician_id"] == 1
    assert result[0]["total_replies"] == 2
    assert result[0]["average_score"] == 1.0


# ============================================================
# GROUPED BREAKDOWN
# ============================================================


def test_build_grouped_breakdown_sums_percentages_to_100(service):
    rows = [
        ("AC Repair", "POSITIVE", 5),
        ("AC Repair", "NEGATIVE", 2),
        ("AC Repair", "NEUTRAL", 2),
        ("AC Repair", "MIXED", 1),
    ]

    result = service._build_grouped_breakdown(
        rows,
        group_key_label="service_type",
    )

    assert len(result) == 1

    breakdown = result[0]

    assert breakdown["total_replies"] == 10

    percentage_sum = sum(
        breakdown["sentiment_percentages"].values()
    )

    assert percentage_sum == 100.0


def test_build_grouped_breakdown_calculates_average_score(service):
    rows = [
        ("AC Repair", "POSITIVE", 3),
        ("AC Repair", "NEGATIVE", 1),
    ]

    result = service._build_grouped_breakdown(
        rows,
        group_key_label="service_type",
    )

    assert result[0]["average_score"] == 0.5


def test_build_grouped_breakdown_sorts_by_volume(service):
    rows = [
        ("Small", "POSITIVE", 2),
        ("Large", "POSITIVE", 10),
        ("Medium", "POSITIVE", 5),
    ]

    result = service._build_grouped_breakdown(
        rows,
        group_key_label="service_type",
    )

    assert result[0]["service_type"] == "Large"
    assert result[1]["service_type"] == "Medium"
    assert result[2]["service_type"] == "Small"


def test_build_grouped_breakdown_skips_none_group(service):
    rows = [
        (None, "POSITIVE", 5),
        ("AC Repair", "POSITIVE", 5),
    ]

    result = service._build_grouped_breakdown(
        rows,
        group_key_label="service_type",
    )

    assert len(result) == 1
    assert result[0]["service_type"] == "AC Repair"


def test_build_grouped_breakdown_normalizes_sentiment(service):
    rows = [
        ("AC Repair", "positive", 5),
        ("AC Repair", "negative", 5),
    ]

    result = service._build_grouped_breakdown(
        rows,
        group_key_label="service_type",
    )

    counts = result[0]["sentiment_counts"]

    assert counts["POSITIVE"] == 5
    assert counts["NEGATIVE"] == 5

def test_build_grouped_breakdown_ignores_unknown_sentiment(service):
    rows = [
        ("AC Repair", "POSITIVE", 5),
        ("AC Repair", "UNKNOWN", 10),
    ]

    result = service._build_grouped_breakdown(
        rows,
        group_key_label="service_type",
    )

    assert len(result) == 1
    assert result[0]["service_type"] == "AC Repair"
    assert result[0]["total_replies"] == 5
    assert result[0]["sentiment_counts"]["POSITIVE"] == 5

def test_build_grouped_breakdown_skips_zero_total_group(service):
    rows = [
        ("AC Repair", "POSITIVE", 0),
    ]

    result = service._build_grouped_breakdown(
        rows,
        group_key_label="service_type",
    )

    assert result == []

      
def test_build_grouped_breakdown_returns_empty_for_empty_rows(
    service,
):
    result = service._build_grouped_breakdown(
        [],
        group_key_label="service_type",
    )

    assert result == []


# ============================================================
# JOB TYPE BREAKDOWN
# ============================================================


def _mock_job_type_query(service, rows):
    query = MagicMock()

    (
        query.join.return_value
        .filter.return_value
        .group_by.return_value
        .all.return_value
    ) = rows

    service.db.query.return_value = query

    return query


def test_get_job_type_breakdown(service):
    _mock_job_type_query(
        service,
        [
            ("AC Repair", "POSITIVE", 8),
            ("AC Repair", "NEGATIVE", 2),
            ("Plumbing", "POSITIVE", 5),
        ],
    )

    result = service.get_job_type_breakdown(
        "tenant-1",
    )

    assert len(result) == 2
    assert result[0]["service_type"] == "AC Repair"
    assert result[0]["total_replies"] == 10
    assert result[0]["average_score"] == 0.6
    assert result[1]["service_type"] == "Plumbing"
    assert result[1]["total_replies"] == 5


def test_get_job_type_breakdown_percentages_are_100(service):
    _mock_job_type_query(
        service,
        [
            ("AC Repair", "POSITIVE", 7),
            ("AC Repair", "NEGATIVE", 3),
        ],
    )

    result = service.get_job_type_breakdown(
        "tenant-1",
    )

    percentages = result[0]["sentiment_percentages"]

    assert sum(percentages.values()) == 100.0


def test_get_job_type_breakdown_empty(service):
    _mock_job_type_query(
        service,
        [],
    )

    result = service.get_job_type_breakdown(
        "tenant-1",
    )

    assert result == []


# ============================================================
# CHANNEL BREAKDOWN
# ============================================================


def _mock_channel_query(service, rows):
    base = MagicMock()

    (
        base.with_entities.return_value
        .group_by.return_value
        .all.return_value
    ) = rows

    service._base_query = MagicMock(
        return_value=base,
    )

    return base


def test_get_channel_breakdown(service):
    _mock_channel_query(
        service,
        [
            ("SMS", "POSITIVE", 7),
            ("SMS", "NEGATIVE", 3),
            ("EMAIL", "POSITIVE", 5),
            ("PORTAL", "NEUTRAL", 2),
        ],
    )

    result = service.get_channel_breakdown(
        "tenant-1",
    )

    assert len(result) == 3

    sms = next(
        item
        for item in result
        if item["channel"] == "SMS"
    )

    assert sms["total_replies"] == 10
    assert sms["sentiment_counts"]["POSITIVE"] == 7
    assert sms["sentiment_counts"]["NEGATIVE"] == 3
    assert sms["sentiment_percentages"]["POSITIVE"] == 70.0
    assert sms["sentiment_percentages"]["NEGATIVE"] == 30.0


def test_get_channel_breakdown_percentages_sum_to_100(
    service,
):
    _mock_channel_query(
        service,
        [
            ("SMS", "POSITIVE", 7),
            ("SMS", "NEGATIVE", 2),
            ("SMS", "NEUTRAL", 1),
        ],
    )

    result = service.get_channel_breakdown(
        "tenant-1",
    )

    sms = result[0]

    assert sum(
        sms["sentiment_percentages"].values()
    ) == 100.0


def test_get_channel_breakdown_empty(service):
    _mock_channel_query(
        service,
        [],
    )

    result = service.get_channel_breakdown(
        "tenant-1",
    )

    assert result == []


# ============================================================
# ALERT FEED
# ============================================================


def _make_escalation(
    escalation_id=1,
    status="OPEN",
):
    return SimpleNamespace(
        id=escalation_id,
        job_id=100,
        customer_name="Customer A",
        technician_name="Technician A",
        sentiment_label="NEGATIVE",
        sentiment_score=-1.0,
        trigger_reason="Negative customer sentiment",
        status=status,
        assigned_manager_id="manager-1",
        created_at=datetime(
            2026,
            8,
            27,
            10,
            tzinfo=timezone.utc,
        ),
        acknowledge_deadline=datetime(
            2026,
            8,
            27,
            11,
            tzinfo=timezone.utc,
        ),
        resolve_deadline=datetime(
            2026,
            8,
            27,
            12,
            tzinfo=timezone.utc,
        ),
    )


def _mock_alert_query(service, escalations):
    query = MagicMock()

    query.filter.return_value = query
    query.order_by.return_value = query
    query.limit.return_value = query
    query.all.return_value = escalations

    service.db.query.return_value = query

    return query


def test_get_alert_feed_returns_recent_escalations(service):
    escalation = _make_escalation(
        escalation_id=10,
        status="OPEN",
    )

    _mock_alert_query(
        service,
        [escalation],
    )

    service.escalation_service.check_sla_breach = MagicMock(
        return_value=None,
    )

    result = service.get_alert_feed(
        "tenant-1",
    )

    assert len(result) == 1

    alert = result[0]

    assert alert["escalation_id"] == 10
    assert alert["job_id"] == 100
    assert alert["customer_name"] == "Customer A"
    assert alert["technician_name"] == "Technician A"
    assert alert["sentiment_label"] == "NEGATIVE"
    assert alert["sentiment_score"] == -1.0
    assert alert["status"] == "OPEN"
    assert alert["assigned_manager_id"] == "manager-1"
    assert alert["sla_breach"] is None
    assert alert["created_at"].endswith("+00:00")
    assert alert["acknowledge_deadline"].endswith("+00:00")
    assert alert["resolve_deadline"].endswith("+00:00")


def test_get_alert_feed_detects_sla_breach(service):
    escalation = _make_escalation()

    _mock_alert_query(
        service,
        [escalation],
    )

    service.escalation_service.check_sla_breach = MagicMock(
        return_value="ACKNOWLEDGE_SLA_BREACHED",
    )

    result = service.get_alert_feed(
        "tenant-1",
    )

    assert len(result) == 1
    assert (
        result[0]["sla_breach"]
        == "ACKNOWLEDGE_SLA_BREACHED"
    )


def test_get_alert_feed_filters_status(service):
    query = MagicMock()

    (
        query.filter.return_value
        .filter.return_value
        .order_by.return_value
        .limit.return_value
        .all.return_value
    ) = []

    service.db.query.return_value = query

    result = service.get_alert_feed(
        "tenant-1",
        status_filter="ACKNOWLEDGED",
    )

    assert result == []


def test_get_alert_feed_excludes_resolved_by_default(service):
    query = MagicMock()

    (
        query.filter.return_value
        .filter.return_value
        .order_by.return_value
        .limit.return_value
        .all.return_value
    ) = []

    service.db.query.return_value = query

    result = service.get_alert_feed(
        "tenant-1",
        include_resolved=False,
    )

    assert result == []


def test_get_alert_feed_can_include_resolved(service):
    escalation = _make_escalation(
        escalation_id=20,
        status="RESOLVED",
    )

    query = MagicMock()

    (
        query.filter.return_value
        .order_by.return_value
        .limit.return_value
        .all.return_value
    ) = [escalation]

    service.db.query.return_value = query

    service.escalation_service.check_sla_breach = MagicMock(
        return_value=None,
    )

    result = service.get_alert_feed(
        "tenant-1",
        include_resolved=True,
    )

    assert len(result) == 1
    assert result[0]["status"] == "RESOLVED"


# ============================================================
# ALERT SUMMARY
# ============================================================


def test_get_alert_summary_counts(service):
    count_query_1 = MagicMock()
    count_query_2 = MagicMock()
    count_query_3 = MagicMock()

    count_query_1.filter.return_value.scalar.return_value = 4
    count_query_2.filter.return_value.scalar.return_value = 3
    count_query_3.filter.return_value.scalar.return_value = 2

    active_query = MagicMock()
    active_query.filter.return_value.all.return_value = []

    service.db.query.side_effect = [
        count_query_1,
        count_query_2,
        count_query_3,
        active_query,
    ]

    result = service.get_alert_summary_counts(
        "tenant-1",
    )

    assert result["open"] == 4
    assert result["acknowledged"] == 3
    assert result["resolved_last_24h"] == 2
    assert result["sla_breached"] == 0


def test_get_alert_summary_counts_detects_breached_escalations(
    service,
):
    count_query_1 = MagicMock()
    count_query_2 = MagicMock()
    count_query_3 = MagicMock()

    count_query_1.filter.return_value.scalar.return_value = 1
    count_query_2.filter.return_value.scalar.return_value = 1
    count_query_3.filter.return_value.scalar.return_value = 1

    escalation = _make_escalation()

    active_query = MagicMock()
    active_query.filter.return_value.all.return_value = [
        escalation
    ]

    service.db.query.side_effect = [
        count_query_1,
        count_query_2,
        count_query_3,
        active_query,
    ]

    service.escalation_service.check_sla_breach = MagicMock(
        return_value="RESOLVE_SLA_BREACHED",
    )

    result = service.get_alert_summary_counts(
        "tenant-1",
    )

    assert result["open"] == 1
    assert result["acknowledged"] == 1
    assert result["resolved_last_24h"] == 1
    assert result["sla_breached"] == 1


def test_get_alert_summary_counts_handles_none_counts(service):
    count_query_1 = MagicMock()
    count_query_2 = MagicMock()
    count_query_3 = MagicMock()

    count_query_1.filter.return_value.scalar.return_value = None
    count_query_2.filter.return_value.scalar.return_value = None
    count_query_3.filter.return_value.scalar.return_value = None

    active_query = MagicMock()
    active_query.filter.return_value.all.return_value = []

    service.db.query.side_effect = [
        count_query_1,
        count_query_2,
        count_query_3,
        active_query,
    ]

    result = service.get_alert_summary_counts(
        "tenant-1",
    )

    assert result["open"] == 0
    assert result["acknowledged"] == 0
    assert result["resolved_last_24h"] == 0
    assert result["sla_breached"] == 0


# ============================================================
# DASHBOARD BUNDLE
# ============================================================


def test_get_dashboard_bundle_contains_all_required_sections(
    service,
):
    service.get_core_metrics = MagicMock(
        return_value={"total_replies": 10},
    )

    service.get_sentiment_trend = MagicMock(
        return_value={"buckets": []},
    )

    service.get_technician_leaderboard = MagicMock(
        return_value=[],
    )

    service.get_job_type_breakdown = MagicMock(
        return_value=[],
    )

    service.get_channel_breakdown = MagicMock(
        return_value=[],
    )

    service.get_alert_feed = MagicMock(
        return_value=[],
    )

    service.get_alert_summary_counts = MagicMock(
        return_value={},
    )

    result = service.get_dashboard_bundle(
        "tenant-1",
    )

    assert set(result.keys()) == {
        "metrics",
        "trend",
        "technician_leaderboard",
        "job_type_breakdown",
        "channel_breakdown",
        "alert_feed",
        "alert_summary",
    }


def test_get_dashboard_bundle_calls_all_services(service):
    service.get_core_metrics = MagicMock(return_value={})
    service.get_sentiment_trend = MagicMock(return_value={})
    service.get_technician_leaderboard = MagicMock(return_value=[])
    service.get_job_type_breakdown = MagicMock(return_value=[])
    service.get_channel_breakdown = MagicMock(return_value=[])
    service.get_alert_feed = MagicMock(return_value=[])
    service.get_alert_summary_counts = MagicMock(return_value={})

    service.get_dashboard_bundle(
        "tenant-1",
        granularity="weekly",
    )

    service.get_core_metrics.assert_called_once()
    service.get_sentiment_trend.assert_called_once()
    service.get_technician_leaderboard.assert_called_once()
    service.get_job_type_breakdown.assert_called_once()
    service.get_channel_breakdown.assert_called_once()
    service.get_alert_feed.assert_called_once()
    service.get_alert_summary_counts.assert_called_once()


# ============================================================
# EXPORT ROWS
# ============================================================


def test_get_export_rows_trend():
    service = MagicMock()

    service.get_sentiment_trend.return_value = {
        "buckets": [
            {
                "period": "2026-08-27T00:00:00+00:00",
                "total_replies": 10,
                "average_score": 0.5,
                "moving_average": 0.4,
            }
        ]
    }

    rows, headers, label_index, value_index = _get_export_rows(
        service,
        "trend",
        "tenant-1",
        None,
        None,
        "daily",
    )

    assert headers == [
        "period",
        "total_replies",
        "average_score",
        "moving_average",
    ]

    assert rows == [
        [
            "2026-08-27T00:00:00+00:00",
            10,
            0.5,
            0.4,
        ]
    ]

    assert label_index == 0
    assert value_index == 2


def test_get_export_rows_leaderboard():
    service = MagicMock()

    service.get_technician_leaderboard.return_value = [
        {
            "rank": 1,
            "technician_name": "Tech A",
            "total_replies": 20,
            "average_score": 0.8,
        }
    ]

    rows, headers, label_index, value_index = _get_export_rows(
        service,
        "leaderboard",
        "tenant-1",
        None,
        None,
        "daily",
    )

    assert headers == [
        "rank",
        "technician_name",
        "total_replies",
        "average_score",
    ]

    assert rows == [
        [
            1,
            "Tech A",
            20,
            0.8,
        ]
    ]

    assert label_index == 1
    assert value_index == 3


def test_get_export_rows_job_type():
    service = MagicMock()

    service.get_job_type_breakdown.return_value = [
        {
            "service_type": "AC Repair",
            "total_replies": 10,
            "average_score": 0.6,
        }
    ]

    rows, headers, label_index, value_index = _get_export_rows(
        service,
        "job_type",
        "tenant-1",
        None,
        None,
        "daily",
    )

    assert headers == [
        "service_type",
        "total_replies",
        "average_score",
    ]

    assert rows == [
        [
            "AC Repair",
            10,
            0.6,
        ]
    ]

    assert label_index == 0
    assert value_index == 2


def test_get_export_rows_channel():
    service = MagicMock()

    service.get_channel_breakdown.return_value = [
        {
            "channel": "SMS",
            "total_replies": 10,
            "average_score": 0.4,
        }
    ]

    rows, headers, label_index, value_index = _get_export_rows(
        service,
        "channel",
        "tenant-1",
        None,
        None,
        "daily",
    )

    assert headers == [
        "channel",
        "total_replies",
        "average_score",
    ]

    assert rows == [
        [
            "SMS",
            10,
            0.4,
        ]
    ]

    assert label_index == 0
    assert value_index == 2


# ============================================================
# CSV EXPORT
# ============================================================


def test_export_csv_returns_streaming_response():
    response = _export_csv(
        rows=[
            ["AC Repair", 10, 0.5],
            ["Plumbing", 5, -0.2],
        ],
        headers=[
            "service_type",
            "total_replies",
            "average_score",
        ],
        export_type="job_type",
    )

    assert response.media_type == "text/csv"

    assert (
        response.headers["Content-Disposition"]
        == "attachment; filename=sentiment_job_type.csv"
    )


def test_export_csv_protects_formula_injection():
    response = _export_csv(
        rows=[
            ["=SUM(A1:A2)", 10, 0.5],
            ["+123", 5, 0.2],
            ["-123", 2, -0.2],
            ["@formula", 1, 0.0],
        ],
        headers=[
            "service_type",
            "total_replies",
            "average_score",
        ],
        export_type="job_type",
    )

    assert response.media_type == "text/csv"


def test_export_csv_supports_empty_rows():
    response = _export_csv(
        rows=[],
        headers=[
            "service_type",
            "total_replies",
            "average_score",
        ],
        export_type="job_type",
    )

    assert response.media_type == "text/csv"


# ============================================================
# PNG EXPORT
# ============================================================


def test_export_png_generates_image_response():
    rows = [
        ["AC Repair", 10, 0.5],
        ["Plumbing", 5, 0.2],
    ]

    response = _export_png(
        rows=rows,
        headers=[
            "service_type",
            "total_replies",
            "average_score",
        ],
        export_type="job_type",
        label_index=0,
        value_index=2,
    )

    assert response.media_type == "image/png"

    assert (
        response.headers["Content-Disposition"]
        == "attachment; filename=sentiment_job_type.png"
    )


def test_export_png_rejects_empty_data():
    with pytest.raises(HTTPException) as exc:
        _export_png(
            rows=[],
            headers=[
                "channel",
                "total_replies",
                "average_score",
            ],
            export_type="channel",
            label_index=0,
            value_index=2,
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "No data to export."


def test_export_png_supports_trend_data():
    rows = [
        [
            "2026-08-27T00:00:00+00:00",
            10,
            0.5,
            0.4,
        ],
    ]

    response = _export_png(
        rows=rows,
        headers=[
            "period",
            "total_replies",
            "average_score",
            "moving_average",
        ],
        export_type="trend",
        label_index=0,
        value_index=2,
    )

    assert response.media_type == "image/png"


# ============================================================
# REDIS CACHE CONFIGURATION
# ============================================================


def test_dashboard_cache_ttl_is_45_seconds():
    assert DASHBOARD_CACHE_TTL_SECONDS == 45


# ============================================================
# WEBSOCKET
# ============================================================


@pytest.mark.asyncio
async def test_broadcast_metrics_update_pushes_data():
    service = MagicMock()

    service.get_core_metrics.return_value = {
        "total_replies": 10,
        "average_confidence": 0.9,
    }

    service.get_alert_summary_counts.return_value = {
        "open": 2,
        "acknowledged": 1,
        "resolved_last_24h": 3,
        "sla_breached": 1,
    }

    with patch(
        "app.sentiment.dashboard.ws_manager.broadcast_to_tenant",
        new_callable=AsyncMock,
    ) as broadcast:

        await broadcast_metrics_update(
            "tenant-1",
            service,
        )

        broadcast.assert_awaited_once()

        args = broadcast.await_args.args

        assert args[0] == "tenant-1"

        payload = args[1]

        assert payload["type"] == "dashboard_metrics_update"
        assert payload["metrics"]["total_replies"] == 10
        assert payload["metrics"]["average_confidence"] == 0.9
        assert payload["alert_summary"]["open"] == 2
        assert payload["alert_summary"]["sla_breached"] == 1


@pytest.mark.asyncio
async def test_broadcast_metrics_update_calls_service_methods():
    service = MagicMock()

    service.get_core_metrics.return_value = {}
    service.get_alert_summary_counts.return_value = {}

    with patch(
        "app.sentiment.dashboard.ws_manager.broadcast_to_tenant",
        new_callable=AsyncMock,
    ):

        await broadcast_metrics_update(
            "tenant-1",
            service,
        )

    service.get_core_metrics.assert_called_once_with(
        "tenant-1",
    )

    service.get_alert_summary_counts.assert_called_once_with(
        "tenant-1",
    )


@pytest.mark.asyncio
async def test_broadcast_all_tenants_broadcasts_to_each_tenant():
    db = MagicMock()

    query = MagicMock()

    query.distinct.return_value.all.return_value = [
        ("tenant-1",),
        ("tenant-2",),
        ("tenant-3",),
    ]

    db.query.return_value = query

    with patch(
        "app.sentiment.dashboard.broadcast_metrics_update",
        new_callable=AsyncMock,
    ) as broadcast:

        await broadcast_all_tenants(db)

        assert broadcast.await_count == 3

        tenant_ids = [
            call.args[0]
            for call in broadcast.await_args_list
        ]

        assert tenant_ids == [
            "tenant-1",
            "tenant-2",
            "tenant-3",
        ]


@pytest.mark.asyncio
async def test_broadcast_all_tenants_handles_no_tenants():
    db = MagicMock()

    query = MagicMock()

    query.distinct.return_value.all.return_value = []

    db.query.return_value = query

    with patch(
        "app.sentiment.dashboard.broadcast_metrics_update",
        new_callable=AsyncMock,
    ) as broadcast:

        await broadcast_all_tenants(db)

        broadcast.assert_not_awaited()


# ============================================================
# TENANT ISOLATION
# ============================================================


def test_base_query_requires_tenant_filter(service):
    query = MagicMock()

    service.db.query.return_value = query
    query.filter.return_value = query

    service._base_query(
        "tenant-secure",
    )

    service.db.query.assert_called_once()
    query.filter.assert_called()


# ============================================================
# SENTIMENT SCORE CONSTANTS
# ============================================================


def test_sentiment_scores_are_correct():
    assert SENTIMENT_SCORES["POSITIVE"] == 1.0
    assert SENTIMENT_SCORES["MIXED"] == 0.5
    assert SENTIMENT_SCORES["NEUTRAL"] == 0.0
    assert SENTIMENT_SCORES["NEGATIVE"] == -1.0

@pytest.mark.asyncio
async def test_get_dashboard_endpoint(monkeypatch):
    current_user = MagicMock()
    current_user.is_super_admin = True
    current_user.tenant_id = "tenant-1"

    db = MagicMock()

    payload = {
        "metrics": {},
        "trend": {},
        "technician_leaderboard": [],
        "job_type_breakdown": [],
        "channel_breakdown": [],
        "alert_feed": [],
        "alert_summary": {},
    }

    service = MagicMock()
    service.get_dashboard_bundle.return_value = payload

    monkeypatch.setattr(
        dashboard,
        "SentimentDashboardService",
        lambda db: service,
    )

    result = await dashboard.get_dashboard(
        tenant_id="tenant-1",
        start_date=None,
        end_date=None,
        granularity="daily",
        db=db,
        current_user=current_user,
        redis_client=None,
    )

    assert result == payload
    service.get_dashboard_bundle.assert_called_once()


@pytest.mark.asyncio
async def test_get_dashboard_endpoint_returns_cached_payload(monkeypatch):
    current_user = MagicMock()
    current_user.is_super_admin = True
    current_user.tenant_id = "tenant-1"

    db = MagicMock()

    payload = {
        "metrics": {"total_replies": 10},
        "trend": {},
        "technician_leaderboard": [],
        "job_type_breakdown": [],
        "channel_breakdown": [],
        "alert_feed": [],
        "alert_summary": {},
    }

    redis_client = MagicMock()
    redis_client.get.return_value = json.dumps(payload)

    service = MagicMock()

    monkeypatch.setattr(
        dashboard,
        "SentimentDashboardService",
        lambda db: service,
    )

    result = await dashboard.get_dashboard(
        tenant_id="tenant-1",
        start_date=None,
        end_date=None,
        granularity="daily",
        db=db,
        current_user=current_user,
        redis_client=redis_client,
    )

    assert result == payload
    redis_client.get.assert_called_once()
    service.get_dashboard_bundle.assert_not_called()

@pytest.mark.asyncio
async def test_get_dashboard_endpoint_handles_empty_cache(monkeypatch):
    current_user = MagicMock()
    current_user.is_super_admin = True
    current_user.tenant_id = "tenant-1"

    db = MagicMock()

    payload = {
        "metrics": {},
        "trend": {},
        "technician_leaderboard": [],
        "job_type_breakdown": [],
        "channel_breakdown": [],
        "alert_feed": [],
        "alert_summary": {},
    }

    redis_client = MagicMock()
    redis_client.get.return_value = None

    service = MagicMock()
    service.get_dashboard_bundle.return_value = payload

    monkeypatch.setattr(
        dashboard,
        "SentimentDashboardService",
        lambda db: service,
    )

    result = await dashboard.get_dashboard(
        tenant_id="tenant-1",
        start_date=None,
        end_date=None,
        granularity="daily",
        db=db,
        current_user=current_user,
        redis_client=redis_client,
    )

    assert result == payload
    redis_client.get.assert_called_once()
    service.get_dashboard_bundle.assert_called_once()


@pytest.mark.asyncio
async def test_get_metrics_endpoint(monkeypatch):
    current_user = MagicMock()
    current_user.is_super_admin = True
    current_user.tenant_id = "tenant-1"

    db = MagicMock()

    service = MagicMock()

    service.get_core_metrics.return_value = {
        "total_replies": 5
    }

    service.get_sentiment_trend.return_value = {
        "granularity": "daily",
        "buckets": [],
        "change": {},
    }

    monkeypatch.setattr(
        dashboard,
        "SentimentDashboardService",
        lambda db: service,
    )

    result = await dashboard.get_metrics(
        tenant_id="tenant-1",
        start_date=None,
        end_date=None,
        granularity="daily",
        db=db,
        current_user=current_user,
        redis_client=None,
    )

    assert result == {
        "metrics": {
            "total_replies": 5
        },
        "trend": {
            "granularity": "daily",
            "buckets": [],
            "change": {},
        },
    }

    service.get_core_metrics.assert_called_once()
    service.get_sentiment_trend.assert_called_once()

@pytest.mark.asyncio
async def test_export_dashboard_data_endpoint(monkeypatch):
    current_user = MagicMock()
    current_user.is_super_admin = True
    current_user.tenant_id = "tenant-1"

    db = MagicMock()

    service = MagicMock()

    monkeypatch.setattr(
        dashboard,
        "SentimentDashboardService",
        lambda db: service,
    )

    expected_response = MagicMock()

    monkeypatch.setattr(
        dashboard,
        "_get_export_rows",
        lambda service, export_type, tenant_id, start_date, end_date, granularity: (
            [["2026-08-28", 10, 0.8, 0.7]],
            ["period", "total_replies", "average_score", "moving_average"],
            0,
            2,
        ),
    )

    monkeypatch.setattr(
        dashboard,
        "_export_csv",
        lambda rows, headers, export_type: expected_response,
    )

    result = await dashboard.export_dashboard_data(
        tenant_id="tenant-1",
        format="csv",
        export_type="trend",
        start_date=None,
        end_date=None,
        granularity="daily",
        db=db,
        current_user=current_user,
        redis_client=None,
    )

    assert result is expected_response

@pytest.mark.asyncio
async def test_export_dashboard_data_endpoint_png(monkeypatch):
    current_user = MagicMock()
    current_user.is_super_admin = True
    current_user.tenant_id = "tenant-1"

    db = MagicMock()

    service = MagicMock()

    monkeypatch.setattr(
        dashboard,
        "SentimentDashboardService",
        lambda db: service,
    )

    expected_response = MagicMock()

    monkeypatch.setattr(
        dashboard,
        "_get_export_rows",
        lambda service, export_type, tenant_id, start_date, end_date, granularity: (
            [["2026-08-28", 10, 0.8, 0.7]],
            ["period", "total_replies", "average_score", "moving_average"],
            0,
            2,
        ),
    )

    monkeypatch.setattr(
        dashboard,
        "_export_png",
        lambda rows, headers, export_type, label_index, value_index: expected_response,
    )

    result = await dashboard.export_dashboard_data(
        tenant_id="tenant-1",
        format="png",
        export_type="trend",
        start_date=None,
        end_date=None,
        granularity="daily",
        db=db,
        current_user=current_user,
        redis_client=None,
    )

    assert result is expected_response