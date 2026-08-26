"""add user notification device fields

Revision ID: 0cd0c66cf970
Revises: bda2aafc2c59
Create Date: 2026-08-26 10:11:31.014629

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0cd0c66cf970'
down_revision: Union[str, Sequence[str], None] = 'bda2aafc2c59'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("fcm_token", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("device_type", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "device_type")
    op.drop_column("users", "fcm_token")
