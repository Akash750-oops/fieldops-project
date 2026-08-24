from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    ForeignKey,
)

from ..models_legacy import Base

class SentimentThreadMessage(Base):
    """
    Stores customer messages and their sentiment results
    for real-time sentiment analysis.
    """

    __tablename__ = "sentiment_thread_messages"

    id = Column(
        Integer,
        primary_key=True,
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

    customer_id = Column(
        String(36),
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    job_id = Column(
        Integer,
        ForeignKey(
            "jobs.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    channel = Column(
        String(20),
        nullable=False,
        index=True,
    )

    message = Column(
        Text,
        nullable=False,
    )

    sentiment = Column(
        String(20),
        nullable=False,
        index=True,
    )

    confidence = Column(
        Float,
        nullable=False,
    )

    emotion = Column(
        String(50),
        nullable=True,
    )

    urgency = Column(
        String(20),
        nullable=True,
    )

    requires_human = Column(
        String(10),
        nullable=True,
    )

    summary = Column(
        Text,
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )