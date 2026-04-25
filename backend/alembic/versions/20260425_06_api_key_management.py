"""api key management: add tracking fields and audit log table

Revision ID: 20260425_06
Revises: 20260425_05
Create Date: 2026-04-25
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "20260425_06"
down_revision = "20260425_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── api_keys: add tracking and revocation columns ─────────────────────────
    op.add_column(
        "api_keys",
        sa.Column("usage_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "api_keys",
        sa.Column("last_used_ip", sa.String(45), nullable=True),
    )
    op.add_column(
        "api_keys",
        sa.Column("last_used_user_agent", sa.String(512), nullable=True),
    )
    op.add_column(
        "api_keys",
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "api_keys",
        sa.Column("revoked_reason", sa.String(255), nullable=True),
    )

    # ── api_key_audit_logs: new table ─────────────────────────────────────────
    op.create_table(
        "api_key_audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("key_id", UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("metadata", JSONB, server_default="{}", nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["key_id"], ["api_keys.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_api_key_audit_logs_user_id", "api_key_audit_logs", ["user_id"])
    op.create_index("ix_api_key_audit_logs_key_id", "api_key_audit_logs", ["key_id"])
    op.create_index("ix_api_key_audit_logs_action", "api_key_audit_logs", ["action"])


def downgrade() -> None:
    op.drop_table("api_key_audit_logs")
    op.drop_column("api_keys", "revoked_reason")
    op.drop_column("api_keys", "revoked_at")
    op.drop_column("api_keys", "last_used_user_agent")
    op.drop_column("api_keys", "last_used_ip")
    op.drop_column("api_keys", "usage_count")
