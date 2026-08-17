"""baseline existing database schema

Revision ID: 004554449425
Revises:
Create Date: 2026-08-10
"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op


revision: str = "004554449425"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the existing database schema from the baseline SQL dump."""

    sql_file = Path(__file__).resolve().parents[2] / "baseline_schema.sql"

    with open(sql_file, "r", encoding="utf-8-sig") as f:
        sql = f.read()

    # Remove psql-specific meta commands.
    lines = []

    for line in sql.splitlines():
        stripped = line.strip()

        if stripped.startswith("\\"):
            continue

        lines.append(line)

    sql = "\n".join(lines)

    op.get_bind().exec_driver_sql(sql)

    # Alembic expects this table to exist so it can record that this
    # migration ran. It isn't part of the app schema, so the baseline
    # dump doesn't create it — create it explicitly here.
    op.get_bind().exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS public.alembic_version (
            version_num VARCHAR(32) NOT NULL,
            CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
        )
        """
    )

    op.get_bind().exec_driver_sql("SET search_path TO public")

def downgrade() -> None:
    """Baseline schema is intentionally not downgraded."""
    pass