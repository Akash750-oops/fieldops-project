from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    event,
    Index,
)

from ..models_legacy import Base


class SentimentAuditRecord(Base):
    """
    Immutable audit trail for sentiment-analysis activities.

    Supported event types:
        - sentiment_analysis
        - escalation
        - manager_action
    """

    __tablename__ = "sentiment_audit_records"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True,
    )

    tenant_id = Column(
        String(50),
        ForeignKey(
            "organizations.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    event_type = Column(
        String(30),
        nullable=False,
        index=True,
    )

    customer_id = Column(
        String(36),
        nullable=True,
        index=True,
    )

    job_id = Column(
        Integer,
        nullable=True,
        index=True,
    )

    manager_id = Column(
        String(36),
        nullable=True,
        index=True,
    )

    # Sentiment analysis fields
    input_text = Column(
        Text,
        nullable=True,
    )

    sentiment_label = Column(
        String(50),
        nullable=True,
        index=True,
    )

    confidence = Column(
        Float,
        nullable=True,
    )

    model_used = Column(
        String(100),
        nullable=True,
    )

    cost = Column(
        Float,
        nullable=True,
    )

    # Escalation fields
    trigger_reason = Column(
        Text,
        nullable=True,
    )

    # Manager action fields
    action = Column(
        String(50),
        nullable=True,
    )

    notes = Column(
        Text,
        nullable=True,
    )

    timestamp = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Tamper-evident hash chain
    sequence_number = Column(
        Integer,
        nullable=False,
    )

    previous_hash = Column(
        String(64),
        nullable=True,
    )

    record_hash = Column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )

    # Retention / archival
    archived_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    __table_args__ = (
        Index(
            "idx_sentiment_audit_tenant_timestamp",
            "tenant_id",
            "timestamp",
        ),
        Index(
            "idx_sentiment_audit_tenant_customer",
            "tenant_id",
            "customer_id",
        ),
        Index(
            "idx_sentiment_audit_tenant_job",
            "tenant_id",
            "job_id",
        ),
        Index(
            "idx_sentiment_audit_tenant_manager",
            "tenant_id",
            "manager_id",
        ),
        Index(
            "idx_sentiment_audit_tenant_sentiment",
            "tenant_id",
            "sentiment_label",
        ),
    )


@event.listens_for(
    SentimentAuditRecord,
    "before_update",
)
def prevent_sentiment_audit_update(
    mapper,
    connection,
    target,
):
    raise ValueError(
        "SentimentAuditRecord is immutable"
    )


@event.listens_for(
    SentimentAuditRecord,
    "before_delete",
)
def prevent_sentiment_audit_delete(
    mapper,
    connection,
    target,
):
    raise ValueError(
        "SentimentAuditRecord is immutable"
    )