"""
Persistent archive for permanently failed task-queue items.
"""

import uuid

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
    JSON,
    Index,
)
from sqlalchemy.sql import func

from ..database import Base


class DeadLetterTask(Base):
    """
    PostgreSQL archive for tasks that permanently fail.

    Redis provides the operational DLQ queue while this table
    provides durable historical storage for inspection, auditing,
    and recovery.
    """

    __tablename__ = "dead_letter_tasks"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # Task identity
    task_id = Column(
        String(100),
        nullable=False,
        index=True,
    )

    celery_task_id = Column(
        String(100),
        nullable=True,
        index=True,
    )

    task_type = Column(
        String(100),
        nullable=True,
        index=True,
    )

    # Multi-tenant ownership
    tenant_id = Column(
        String(50),
        nullable=False,
        index=True,
    )

    # Complete task data
    payload = Column(
        JSON,
        nullable=False,
    )

    context = Column(
        JSON,
        nullable=True,
    )

    # Failure information
    reason = Column(
        String(100),
        nullable=False,
    )

    error_type = Column(
        String(255),
        nullable=True,
    )

    error_message = Column(
        Text,
        nullable=True,
    )

    retry_count = Column(
        Integer,
        nullable=False,
        default=0,
    )

    # Lifecycle
    status = Column(
        String(30),
        nullable=False,
        default="FAILED",
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    failed_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    requeued_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        Index(
            "idx_dead_letter_task_tenant_status",
            "tenant_id",
            "status",
        ),
        Index(
            "idx_dead_letter_task_tenant_created",
            "tenant_id",
            "created_at",
        ),
    )