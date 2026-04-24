"""add email auth fields to users

Revision ID: 20260423_03
Revises: 20260423_02
Create Date: 2026-04-23 16:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260423_03"
down_revision: str | None = "20260423_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("display_name", sa.String(length=255), nullable=True))
    op.add_column(
        "users",
        sa.Column("email_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column("users", sa.Column("auth_provider", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "auth_provider")
    op.drop_column("users", "email_verified")
    op.drop_column("users", "display_name")
