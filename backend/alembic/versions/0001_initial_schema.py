"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-04-26
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the full current schema from the SQLAlchemy model metadata."""
    import app.models  # noqa: F401
    from app.models.base import Base

    bind = op.get_bind()
    bind.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(bind=bind, checkfirst=True)
    _create_agent_embeddings_table()


def downgrade() -> None:
    """Drop the full current schema."""
    import app.models  # noqa: F401
    from app.models.base import Base

    bind = op.get_bind()
    op.execute("DROP TABLE IF EXISTS agent_embeddings")
    Base.metadata.drop_all(bind=bind, checkfirst=True)


def _create_agent_embeddings_table() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_embeddings (
            agent_id UUID PRIMARY KEY REFERENCES agents(id) ON DELETE CASCADE,
            name VARCHAR(100) NOT NULL,
            description TEXT NOT NULL,
            category VARCHAR(100) NOT NULL DEFAULT '',
            tags JSONB NOT NULL DEFAULT '[]'::jsonb,
            rating NUMERIC(3, 2) NOT NULL DEFAULT 0,
            pricing JSONB NOT NULL DEFAULT '{}'::jsonb,
            status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
            embedding vector,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_agent_embeddings_status
        ON agent_embeddings (status)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_agent_embeddings_category
        ON agent_embeddings (category)
        """
    )
