"""add prompt performance analytics tables

Revision ID: 8f6c1e4a2b90
Revises: c5618b3bdac0
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8f6c1e4a2b90"
down_revision: Union[str, Sequence[str], None] = "c5618b3bdac0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "prompt_usage_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("prompt_id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=50), nullable=False),
        sa.Column("agent_type", sa.String(length=50), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("tokens", sa.Integer(), nullable=False),
        sa.Column("fallback", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("error", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("engaged", sa.Boolean(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_prompt_usage_events_prompt_id", "prompt_usage_events", ["prompt_id"])
    op.create_index("ix_prompt_usage_events_tenant_id", "prompt_usage_events", ["tenant_id"])
    op.create_index("ix_prompt_usage_events_agent_type", "prompt_usage_events", ["agent_type"])
    op.create_index("ix_prompt_usage_events_channel", "prompt_usage_events", ["channel"])
    op.create_index("ix_prompt_usage_events_occurred_at", "prompt_usage_events", ["occurred_at"])
    op.create_index("idx_prompt_usage_tenant_time", "prompt_usage_events", ["tenant_id", "occurred_at"])

    op.create_table(
        "prompt_analytics_aggregates",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=50), nullable=False),
        sa.Column("dimension", sa.String(length=20), nullable=False),
        sa.Column("dimension_key", sa.String(length=100), nullable=False),
        sa.Column("period_days", sa.Integer(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_prompt_analytics_aggregates_tenant_id", "prompt_analytics_aggregates", ["tenant_id"])
    op.create_index(
        "uq_prompt_analytics_dimension",
        "prompt_analytics_aggregates",
        ["tenant_id", "dimension", "dimension_key", "period_days"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_prompt_analytics_dimension", table_name="prompt_analytics_aggregates")
    op.drop_index("ix_prompt_analytics_aggregates_tenant_id", table_name="prompt_analytics_aggregates")
    op.drop_table("prompt_analytics_aggregates")
    op.drop_index("idx_prompt_usage_tenant_time", table_name="prompt_usage_events")
    for name in (
        "ix_prompt_usage_events_occurred_at",
        "ix_prompt_usage_events_channel",
        "ix_prompt_usage_events_agent_type",
        "ix_prompt_usage_events_tenant_id",
        "ix_prompt_usage_events_prompt_id",
    ):
        op.drop_index(name, table_name="prompt_usage_events")
    op.drop_table("prompt_usage_events")