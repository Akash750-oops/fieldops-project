"""add sentiment thread messages

Revision ID: b6c489d96dd9
Revises: c5618b3bdac0
Create Date: 2026-08-22

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b6c489d96dd9"
down_revision: Union[str, Sequence[str], None] = "8f6c1e4a2b90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create sentiment thread message storage."""

    op.create_table(
        "sentiment_thread_messages",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            nullable=False,
        ),

        sa.Column(
            "tenant_id",
            sa.String(length=50),
            nullable=False,
        ),

        sa.Column(
            "customer_id",
            sa.String(length=36),
            nullable=False,
        ),

        sa.Column(
            "job_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "channel",
            sa.String(length=20),
            nullable=False,
        ),

        sa.Column(
            "message",
            sa.Text(),
            nullable=False,
        ),

        sa.Column(
            "sentiment",
            sa.String(length=20),
            nullable=False,
        ),

        sa.Column(
            "confidence",
            sa.Float(),
            nullable=False,
        ),

        sa.Column(
            "emotion",
            sa.String(length=50),
            nullable=True,
        ),

        sa.Column(
            "urgency",
            sa.String(length=20),
            nullable=True,
        ),

        sa.Column(
            "requires_human",
            sa.String(length=10),
            nullable=True,
        ),

        sa.Column(
            "summary",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),

        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["organizations.id"],
            ondelete="RESTRICT",
        ),

        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),

        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            ondelete="RESTRICT",
        ),
    )

    op.create_index(
        "ix_sentiment_thread_messages_id",
        "sentiment_thread_messages",
        ["id"],
        unique=False,
    )

    op.create_index(
        "ix_sentiment_thread_messages_tenant_id",
        "sentiment_thread_messages",
        ["tenant_id"],
        unique=False,
    )

    op.create_index(
        "ix_sentiment_thread_messages_customer_id",
        "sentiment_thread_messages",
        ["customer_id"],
        unique=False,
    )

    op.create_index(
        "ix_sentiment_thread_messages_job_id",
        "sentiment_thread_messages",
        ["job_id"],
        unique=False,
    )

    op.create_index(
        "ix_sentiment_thread_messages_channel",
        "sentiment_thread_messages",
        ["channel"],
        unique=False,
    )

    op.create_index(
        "ix_sentiment_thread_messages_sentiment",
        "sentiment_thread_messages",
        ["sentiment"],
        unique=False,
    )

    op.create_index(
        "ix_sentiment_thread_messages_created_at",
        "sentiment_thread_messages",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Remove sentiment thread message storage."""

    op.drop_index(
        "ix_sentiment_thread_messages_created_at",
        table_name="sentiment_thread_messages",
    )

    op.drop_index(
        "ix_sentiment_thread_messages_sentiment",
        table_name="sentiment_thread_messages",
    )

    op.drop_index(
        "ix_sentiment_thread_messages_channel",
        table_name="sentiment_thread_messages",
    )

    op.drop_index(
        "ix_sentiment_thread_messages_job_id",
        table_name="sentiment_thread_messages",
    )

    op.drop_index(
        "ix_sentiment_thread_messages_customer_id",
        table_name="sentiment_thread_messages",
    )

    op.drop_index(
        "ix_sentiment_thread_messages_tenant_id",
        table_name="sentiment_thread_messages",
    )

    op.drop_index(
        "ix_sentiment_thread_messages_id",
        table_name="sentiment_thread_messages",
    )

    op.drop_table("sentiment_thread_messages")