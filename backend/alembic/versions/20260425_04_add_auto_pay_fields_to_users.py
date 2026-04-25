"""add auto_pay fields to users

Revision ID: 20260425_04
Revises: 20260423_03
Create Date: 2026-04-25 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260425_04"
down_revision: str | None = "20260423_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "auto_pay_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column("auto_pay_max_per_job", sa.Numeric(precision=20, scale=6), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("auto_pay_max_per_day", sa.Numeric(precision=20, scale=6), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "auto_pay_max_per_day")
    op.drop_column("users", "auto_pay_max_per_job")
    op.drop_column("users", "auto_pay_enabled")
