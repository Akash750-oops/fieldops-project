"""add dead letter tasks

Revision ID: aba59f63cb44
Revises: 0cd0c66cf970
Create Date: 2026-08-29 10:51:24.606814
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "aba59f63cb44"
down_revision: Union[str, Sequence[str], None] = "0cd0c66cf970"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the persistent dead-letter task archive."""

    op.create_table(
        "dead_letter_tasks",
        sa.Column(
            "id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "task_id",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "celery_task_id",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "task_type",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "tenant_id",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "payload",
            sa.JSON(),
            nullable=False,
        ),
        sa.Column(
            "context",
            sa.JSON(),
            nullable=True,
        ),
        sa.Column(
            "reason",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "error_type",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "retry_count",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "failed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "requeued_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "idx_dead_letter_task_tenant_created",
        "dead_letter_tasks",
        ["tenant_id", "created_at"],
        unique=False,
    )

    op.create_index(
        "idx_dead_letter_task_tenant_status",
        "dead_letter_tasks",
        ["tenant_id", "status"],
        unique=False,
    )

    op.create_index(
        op.f("ix_dead_letter_tasks_celery_task_id"),
        "dead_letter_tasks",
        ["celery_task_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_dead_letter_tasks_created_at"),
        "dead_letter_tasks",
        ["created_at"],
        unique=False,
    )

    op.create_index(
        op.f("ix_dead_letter_tasks_failed_at"),
        "dead_letter_tasks",
        ["failed_at"],
        unique=False,
    )

    op.create_index(
        op.f("ix_dead_letter_tasks_status"),
        "dead_letter_tasks",
        ["status"],
        unique=False,
    )

    op.create_index(
        op.f("ix_dead_letter_tasks_task_id"),
        "dead_letter_tasks",
        ["task_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_dead_letter_tasks_task_type"),
        "dead_letter_tasks",
        ["task_type"],
        unique=False,
    )

    op.create_index(
        op.f("ix_dead_letter_tasks_tenant_id"),
        "dead_letter_tasks",
        ["tenant_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove the persistent dead-letter task archive."""

    op.drop_index(
        op.f("ix_dead_letter_tasks_tenant_id"),
        table_name="dead_letter_tasks",
    )

    op.drop_index(
        op.f("ix_dead_letter_tasks_task_type"),
        table_name="dead_letter_tasks",
    )

    op.drop_index(
        op.f("ix_dead_letter_tasks_task_id"),
        table_name="dead_letter_tasks",
    )

    op.drop_index(
        op.f("ix_dead_letter_tasks_status"),
        table_name="dead_letter_tasks",
    )

    op.drop_index(
        op.f("ix_dead_letter_tasks_failed_at"),
        table_name="dead_letter_tasks",
    )

    op.drop_index(
        op.f("ix_dead_letter_tasks_created_at"),
        table_name="dead_letter_tasks",
    )

    op.drop_index(
        op.f("ix_dead_letter_tasks_celery_task_id"),
        table_name="dead_letter_tasks",
    )

    op.drop_index(
        "idx_dead_letter_task_tenant_status",
        table_name="dead_letter_tasks",
    )

    op.drop_index(
        "idx_dead_letter_task_tenant_created",
        table_name="dead_letter_tasks",
    )

    op.drop_table("dead_letter_tasks")