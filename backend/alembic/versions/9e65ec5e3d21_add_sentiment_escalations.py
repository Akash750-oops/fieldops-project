"""add sentiment escalations

Revision ID: 9e65ec5e3d21
Revises: b6c489d96dd9
Create Date: 2026-08-25 11:59:38.642298

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9e65ec5e3d21"
down_revision: Union[str, Sequence[str], None] = "b6c489d96dd9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create sentiment escalation table."""

    op.create_table(
        "sentiment_escalations",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),

        sa.Column(
            "tenant_id",
            sa.String(length=50),
            nullable=False,
        ),

        sa.Column(
            "job_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "customer_id",
            sa.String(length=36),
            nullable=False,
        ),

        sa.Column(
            "customer_name",
            sa.String(length=200),
            nullable=False,
        ),

        sa.Column(
            "technician_name",
            sa.String(length=200),
            nullable=True,
        ),

        sa.Column(
            "reply_text",
            sa.Text(),
            nullable=False,
        ),

        sa.Column(
            "sentiment_label",
            sa.String(length=50),
            nullable=False,
        ),

        sa.Column(
            "sentiment_score",
            sa.Float(),
            nullable=False,
        ),

        sa.Column(
            "trigger_reason",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "suggested_action",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "assigned_manager_id",
            sa.String(length=36),
            nullable=True,
        ),

        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="OPEN",
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),

        sa.Column(
            "acknowledged_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "resolved_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "acknowledge_deadline",
            sa.DateTime(timezone=True),
            nullable=False,
        ),

        sa.Column(
            "resolve_deadline",
            sa.DateTime(timezone=True),
            nullable=False,
        ),

        sa.Column(
            "resolution_notes",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),

        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["organizations.id"],
            ondelete="RESTRICT",
        ),

        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            ondelete="RESTRICT",
        ),

        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),

        sa.ForeignKeyConstraint(
            ["assigned_manager_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
    )

    # Indexes created by index=True in the SQLAlchemy model.
    op.create_index(
        "ix_sentiment_escalations_id",
        "sentiment_escalations",
        ["id"],
        unique=False,
    )

    op.create_index(
        "ix_sentiment_escalations_tenant_id",
        "sentiment_escalations",
        ["tenant_id"],
        unique=False,
    )

    op.create_index(
        "ix_sentiment_escalations_job_id",
        "sentiment_escalations",
        ["job_id"],
        unique=False,
    )

    op.create_index(
        "ix_sentiment_escalations_customer_id",
        "sentiment_escalations",
        ["customer_id"],
        unique=False,
    )

    op.create_index(
        "ix_sentiment_escalations_sentiment_label",
        "sentiment_escalations",
        ["sentiment_label"],
        unique=False,
    )

    op.create_index(
        "ix_sentiment_escalations_trigger_reason",
        "sentiment_escalations",
        ["trigger_reason"],
        unique=False,
    )

    op.create_index(
        "ix_sentiment_escalations_assigned_manager_id",
        "sentiment_escalations",
        ["assigned_manager_id"],
        unique=False,
    )

    op.create_index(
        "ix_sentiment_escalations_status",
        "sentiment_escalations",
        ["status"],
        unique=False,
    )

    op.create_index(
        "ix_sentiment_escalations_created_at",
        "sentiment_escalations",
        ["created_at"],
        unique=False,
    )

    # Additional composite indexes from the model.
    op.create_index(
        "idx_sentiment_escalations_tenant_job_created",
        "sentiment_escalations",
        ["tenant_id", "job_id", "created_at"],
        unique=False,
    )

    op.create_index(
        "idx_sentiment_escalations_tenant_status",
        "sentiment_escalations",
        ["tenant_id", "status"],
        unique=False,
    )

    op.create_index(
        "idx_sentiment_escalations_tenant_manager",
        "sentiment_escalations",
        ["tenant_id", "assigned_manager_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove sentiment escalation table."""

    op.drop_index(
        "idx_sentiment_escalations_tenant_manager",
        table_name="sentiment_escalations",
    )

    op.drop_index(
        "idx_sentiment_escalations_tenant_status",
        table_name="sentiment_escalations",
    )

    op.drop_index(
        "idx_sentiment_escalations_tenant_job_created",
        table_name="sentiment_escalations",
    )

    op.drop_index(
        "ix_sentiment_escalations_created_at",
        table_name="sentiment_escalations",
    )

    op.drop_index(
        "ix_sentiment_escalations_status",
        table_name="sentiment_escalations",
    )

    op.drop_index(
        "ix_sentiment_escalations_assigned_manager_id",
        table_name="sentiment_escalations",
    )

    op.drop_index(
        "ix_sentiment_escalations_trigger_reason",
        table_name="sentiment_escalations",
    )

    op.drop_index(
        "ix_sentiment_escalations_sentiment_label",
        table_name="sentiment_escalations",
    )

    op.drop_index(
        "ix_sentiment_escalations_customer_id",
        table_name="sentiment_escalations",
    )

    op.drop_index(
        "ix_sentiment_escalations_job_id",
        table_name="sentiment_escalations",
    )

    op.drop_index(
        "ix_sentiment_escalations_tenant_id",
        table_name="sentiment_escalations",
    )

    op.drop_index(
        "ix_sentiment_escalations_id",
        table_name="sentiment_escalations",
    )

    op.drop_table("sentiment_escalations")