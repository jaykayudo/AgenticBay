"""initial_schema

Revision ID: fbe02a9ce655
Revises:
Create Date: 2026-04-24

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "fbe02a9ce655"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── Enum types ──────────────────────────────────────────────────────────
    op.execute(
        "CREATE TYPE user_role AS ENUM ('BUYER','AGENT_OWNER','BOTH','ADMIN')"
    )
    op.execute(
        "CREATE TYPE user_status AS ENUM ('ACTIVE','SUSPENDED','BANNED','PENDING')"
    )
    op.execute(
        "CREATE TYPE auth_provider_type AS ENUM ('GOOGLE','FACEBOOK','EMAIL')"
    )
    op.execute(
        "CREATE TYPE api_key_environment AS ENUM ('SANDBOX','PRODUCTION')"
    )
    op.execute(
        "CREATE TYPE agent_hosting_type AS ENUM ('EXTERNALLY_HOSTED')"
    )
    op.execute(
        "CREATE TYPE agent_status AS ENUM ('PENDING','ACTIVE','PAUSED','SUSPENDED','REJECTED')"
    )
    op.execute(
        "CREATE TYPE session_phase AS ENUM "
        "('STARTED','SEARCHING','CONNECTING','ACTIVE','AWAITING_PAYMENT','CLOSING','CLOSED')"
    )
    op.execute(
        "CREATE TYPE connection_type AS ENUM ('WEBSOCKET','WEBHOOK')"
    )
    op.execute(
        "CREATE TYPE message_direction AS ENUM ('INBOUND','OUTBOUND')"
    )
    op.execute(
        "CREATE TYPE agent_type AS ENUM ('USER','ORCHESTRATOR','SERVICE')"
    )
    op.execute(
        "CREATE TYPE job_status AS ENUM "
        "('AWAITING_INVOICE','INVOICE_GENERATED','AWAITING_PAYMENT','PAYMENT_VERIFIED',"
        "'IN_PROGRESS','COMPLETED','FAILED','DISPUTED','REFUNDED','EXPIRED')"
    )
    op.execute(
        "CREATE TYPE invoice_status AS ENUM "
        "('PENDING','PAYMENT_CHECKING','PENDING_RELEASE','DISBURSING',"
        "'DISBURSED','REFUNDED','EXPIRED','FAILED')"
    )
    op.execute(
        "CREATE TYPE escrow_wallet_status AS ENUM "
        "('AVAILABLE','LOCKED','DRAINING','MAINTENANCE')"
    )
    op.execute(
        "CREATE TYPE transaction_type AS ENUM "
        "('DEPOSIT','WITHDRAWAL','JOB_PAYMENT','FEE','REFUND','EARNING')"
    )
    op.execute(
        "CREATE TYPE transaction_status AS ENUM "
        "('INITIATED','PENDING','CONFIRMED','FAILED','REFUNDED')"
    )
    op.execute(
        "CREATE TYPE analytic_period AS ENUM ('DAILY','WEEKLY','MONTHLY')"
    )
    op.execute(
        "CREATE TYPE notification_type AS ENUM "
        "('JOB_STARTED','JOB_COMPLETED','JOB_FAILED','PAYMENT_SENT','PAYMENT_RECEIVED',"
        "'PAYMENT_CONFIRMED','AGENT_CONNECTED','SESSION_CLOSED','REVIEW_POSTED',"
        "'SYSTEM_ALERT','PAYOUT_SENT','REFUND_ISSUED')"
    )
    op.execute(
        "CREATE TYPE review_status AS ENUM ('PENDING','PUBLISHED','REMOVED')"
    )

    # ── users ───────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("username", sa.String(100), unique=True, nullable=True),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("role", sa.Enum("BUYER","AGENT_OWNER","BOTH","ADMIN", name="user_role", create_type=False), nullable=False),
        sa.Column("status", sa.Enum("ACTIVE","SUSPENDED","BANNED","PENDING", name="user_status", create_type=False), nullable=False),
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("kyc_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("wallet_address", sa.String(255), unique=True, nullable=True),
        sa.Column("per_job_spend_limit", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("daily_spend_limit", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("confirm_above", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("notification_preferences", postgresql.JSONB(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_wallet_address", "users", ["wallet_address"])

    # ── user auth providers ─────────────────────────────────────────────────
    op.create_table(
        "user_auth_providers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("provider", sa.Enum("GOOGLE","FACEBOOK","EMAIL", name="auth_provider_type", create_type=False), nullable=False),
        sa.Column("provider_user_id", sa.String(255), nullable=False),
        sa.Column("provider_email", sa.String(255), nullable=True),
        sa.Column("provider_data", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.UniqueConstraint("user_id", "provider", name="uq_user_auth_providers_user_provider"),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_user_auth_providers_provider_uid"),
    )

    # ── auth sessions ───────────────────────────────────────────────────────
    op.create_table(
        "auth_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("token_prefix", sa.String(20), nullable=False),
        sa.Column("refresh_token_hash", sa.String(255), nullable=False),
        sa.Column("device_info", sa.String(500), nullable=True),
        sa.Column("ip_address", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── api_keys ────────────────────────────────────────────────────────────
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("key_prefix", sa.String(20), nullable=False),
        sa.Column("key_hash", sa.String(255), nullable=False),
        sa.Column("environment", sa.Enum("SANDBOX","PRODUCTION", name="api_key_environment", create_type=False), nullable=False),
        sa.Column("permissions", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    )

    # ── agents ──────────────────────────────────────────────────────────────
    op.create_table(
        "agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), unique=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("profile_image_url", sa.String(500), nullable=True),
        sa.Column("hosting_type", sa.Enum("EXTERNALLY_HOSTED", name="agent_hosting_type", create_type=False), nullable=False),
        sa.Column("base_url", sa.String(500), nullable=True),
        sa.Column("status", sa.Enum("PENDING","ACTIVE","PAUSED","SUSPENDED","REJECTED", name="agent_status", create_type=False), nullable=False),
        sa.Column("categories", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("tags", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("wallet_address", sa.String(255), nullable=True),
        sa.Column("orchestrator_api_key", sa.String(255), unique=True, nullable=True),
        sa.Column("capabilities_cache", postgresql.JSONB(), nullable=True),
        sa.Column("pricing_summary", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("total_jobs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_rate", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0"),
        sa.Column("avg_rating", sa.Numeric(precision=3, scale=2), nullable=False, server_default="0"),
        sa.Column("total_earned", sa.Numeric(precision=18, scale=6), nullable=False, server_default="0"),
        sa.Column("avg_duration_sec", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0"),
    )
    op.create_index("ix_agents_status", "agents", ["status"])
    op.create_index("ix_agents_slug", "agents", ["slug"])

    # ── agent_actions ───────────────────────────────────────────────────────
    op.create_table(
        "agent_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("input_schema", postgresql.JSONB(), nullable=True),
        sa.Column("output_schema", postgresql.JSONB(), nullable=True),
        sa.Column("price", sa.Numeric(precision=18, scale=6), nullable=True),
    )

    # ── escrow_wallets ──────────────────────────────────────────────────────
    op.create_table(
        "escrow_wallets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("circle_wallet_id", sa.String(255), unique=True, nullable=False),
        sa.Column("circle_wallet_set_id", sa.String(255), nullable=True),
        sa.Column("wallet_address", sa.String(255), unique=True, nullable=False),
        sa.Column("blockchain", sa.String(50), nullable=False, server_default="ARC-TESTNET"),
        sa.Column("status", sa.Enum("AVAILABLE","LOCKED","DRAINING","MAINTENANCE", name="escrow_wallet_status", create_type=False), nullable=False, server_default="AVAILABLE"),
        sa.Column("locked_invoice_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("current_balance", sa.Numeric(precision=18, scale=6), nullable=False, server_default="0"),
        sa.Column("last_balance_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_lifetime_volume", sa.Numeric(precision=18, scale=6), nullable=False, server_default="0"),
        sa.Column("times_used", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_escrow_wallets_status", "escrow_wallets", ["status"])
    op.create_index("ix_escrow_wallets_locked_invoice_id", "escrow_wallets", ["locked_invoice_id"])

    # ── sessions ────────────────────────────────────────────────────────────
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("phase", sa.Enum("STARTED","SEARCHING","CONNECTING","ACTIVE","AWAITING_PAYMENT","CLOSING","CLOSED", name="session_phase", create_type=False), nullable=False),
        sa.Column("connection_type", sa.Enum("WEBSOCKET","WEBHOOK", name="connection_type", create_type=False), nullable=False),
        sa.Column("job_session_auth_token", sa.String(512), nullable=False),
        sa.Column("webhook_url", sa.String(500), nullable=True),
        sa.Column("hmac_secret", sa.String(255), nullable=True),
        sa.Column("graph_state", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_index("ix_sessions_phase", "sessions", ["phase"])

    # ── messages ────────────────────────────────────────────────────────────
    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("direction", sa.Enum("INBOUND","OUTBOUND", name="message_direction", create_type=False), nullable=False),
        sa.Column("from_agent_type", sa.Enum("USER","ORCHESTRATOR","SERVICE", name="agent_type", create_type=False), nullable=False),
        sa.Column("to_agent_type", sa.Enum("USER","ORCHESTRATOR","SERVICE", name="agent_type", create_type=False), nullable=False),
        sa.Column("message_type", sa.String(50), nullable=False, index=True),
        sa.Column("content", sa.Text(), nullable=False),
    )

    # ── jobs ────────────────────────────────────────────────────────────────
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("buyer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("action_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_actions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.Enum("AWAITING_INVOICE","INVOICE_GENERATED","AWAITING_PAYMENT","PAYMENT_VERIFIED","IN_PROGRESS","COMPLETED","FAILED","DISPUTED","REFUNDED","EXPIRED", name="job_status", create_type=False), nullable=False),
        sa.Column("raw_user_request", sa.Text(), nullable=True),
        sa.Column("llm_interpretation", postgresql.JSONB(), nullable=True),
        sa.Column("action_inputs", postgresql.JSONB(), nullable=True),
        sa.Column("service_response", postgresql.JSONB(), nullable=True),
        sa.Column("formatted_response", postgresql.JSONB(), nullable=True),
        sa.Column("quality_score", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_jobs_status", "jobs", ["status"])

    # ── invoices ────────────────────────────────────────────────────────────
    op.create_table(
        "invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), unique=True, nullable=False, index=True),
        sa.Column("payer_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("service_agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("escrow_wallet_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("escrow_wallets.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("amount", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("marketplace_fee", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("agent_payout", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USDC"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.Enum("PENDING","PAYMENT_CHECKING","PENDING_RELEASE","DISBURSING","DISBURSED","REFUNDED","EXPIRED","FAILED", name="invoice_status", create_type=False), nullable=False, server_default="PENDING"),
        sa.Column("payer_wallet_address", sa.String(255), nullable=True),
        sa.Column("payee_wallet_address", sa.String(255), nullable=True),
        sa.Column("marketplace_wallet_address", sa.String(255), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disbursed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payment_transaction_id", sa.String(255), nullable=True),
        sa.Column("payment_tx_hash", sa.String(255), nullable=True),
        sa.Column("payment_tx_url", sa.String(500), nullable=True),
        sa.Column("agent_disbursement_tx_id", sa.String(255), nullable=True),
        sa.Column("agent_disbursement_tx_hash", sa.String(255), nullable=True),
        sa.Column("fee_disbursement_tx_id", sa.String(255), nullable=True),
        sa.Column("fee_disbursement_tx_hash", sa.String(255), nullable=True),
        sa.Column("refund_tx_id", sa.String(255), nullable=True),
        sa.Column("refund_tx_hash", sa.String(255), nullable=True),
    )
    op.create_index("ix_invoices_session_status", "invoices", ["session_id", "status"])
    op.create_index("ix_invoices_status_expires", "invoices", ["status", "expires_at"])

    # ── wallet_transactions ─────────────────────────────────────────────────
    op.create_table(
        "wallet_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("transaction_type", sa.Enum("DEPOSIT","WITHDRAWAL","JOB_PAYMENT","FEE","REFUND","EARNING", name="transaction_type", create_type=False), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USDC"),
        sa.Column("status", sa.Enum("INITIATED","PENDING","CONFIRMED","FAILED","REFUNDED", name="transaction_status", create_type=False), nullable=False, server_default="INITIATED"),
        sa.Column("circle_transfer_id", sa.String(255), nullable=True, index=True),
        sa.Column("onchain_tx_hash", sa.String(255), nullable=True, index=True),
        sa.Column("from_address", sa.String(255), nullable=True),
        sa.Column("to_address", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
    )

    # ── spending ────────────────────────────────────────────────────────────
    op.create_table(
        "agent_spending",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("master_agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("sub_agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="RESTRICT"), nullable=True, index=True),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("amount", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
    )

    # ── reviews ─────────────────────────────────────────────────────────────
    op.create_table(
        "reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("verified_purchase", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("helpful_votes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.Enum("PENDING","PUBLISHED","REMOVED", name="review_status", create_type=False), nullable=False),
    )

    # ── analytics ───────────────────────────────────────────────────────────
    op.create_table(
        "agent_analytics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("period", sa.Enum("DAILY","WEEKLY","MONTHLY", name="analytic_period", create_type=False), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_jobs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("successful_jobs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_jobs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_revenue", sa.Numeric(precision=18, scale=6), nullable=False, server_default="0"),
        sa.Column("avg_rating", sa.Numeric(precision=3, scale=2), nullable=False, server_default="0"),
        sa.Column("avg_duration_sec", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0"),
        sa.Column("action_breakdown", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.UniqueConstraint("agent_id", "period", "period_start", name="uq_agent_analytics_agent_period"),
    )

    # ── notifications ────────────────────────────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column(
            "notification_type",
            sa.Enum(
                "JOB_STARTED","JOB_COMPLETED","JOB_FAILED","PAYMENT_SENT","PAYMENT_RECEIVED",
                "PAYMENT_CONFIRMED","AGENT_CONNECTED","SESSION_CLOSED","REVIEW_POSTED",
                "SYSTEM_ALERT","PAYOUT_SENT","REFUND_ISSUED",
                name="notification_type", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("data", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("agent_analytics")
    op.drop_table("reviews")
    op.drop_table("agent_spending")
    op.drop_table("wallet_transactions")
    op.drop_table("invoices")
    op.drop_table("jobs")
    op.drop_table("messages")
    op.drop_table("sessions")
    op.drop_table("escrow_wallets")
    op.drop_table("agent_actions")
    op.drop_table("agents")
    op.drop_table("api_keys")
    op.drop_table("auth_sessions")
    op.drop_table("user_auth_providers")
    op.drop_table("users")

    for t in (
        "notification_type", "review_status", "analytic_period",
        "transaction_status", "transaction_type", "escrow_wallet_status",
        "invoice_status", "job_status", "agent_type", "message_direction",
        "connection_type", "session_phase", "agent_status", "agent_hosting_type",
        "api_key_environment", "auth_provider_type", "user_status", "user_role",
    ):
        op.execute(f"DROP TYPE IF EXISTS {t}")
