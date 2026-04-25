"""add agent health fields and health notification types

Revision ID: 20260425_05
Revises: 20260425_04
Create Date: 2026-04-25
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260425_05"
down_revision = "20260425_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── agents table: health tracking columns ─────────────────────────────────
    op.add_column(
        "agents",
        sa.Column("last_health_check_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "agents",
        sa.Column("last_health_status", sa.String(20), nullable=True),
    )
    op.add_column(
        "agents",
        sa.Column(
            "consecutive_health_failures",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "agents",
        sa.Column("agent_version", sa.String(50), nullable=True),
    )

    # ── notification_type enum: add health values ─────────────────────────────
    # ALTER TYPE … ADD VALUE is transactional in Postgres 12+ only when outside
    # an explicit transaction, so we use COMMIT/BEGIN guards.
    op.execute("COMMIT")
    op.execute("ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'AGENT_HEALTH_DEGRADED'")
    op.execute("ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'AGENT_SUSPENDED'")
    op.execute("BEGIN")


def downgrade() -> None:
    # Drop health columns from agents
    op.drop_column("agents", "agent_version")
    op.drop_column("agents", "consecutive_health_failures")
    op.drop_column("agents", "last_health_status")
    op.drop_column("agents", "last_health_check_at")
    # Note: Postgres does not support removing values from an existing enum type.
    # The AGENT_HEALTH_DEGRADED and AGENT_SUSPENDED values will remain in the DB enum.
