"""initial: enable pgvector, create runs table

Revision ID: 0001
Revises:
Create Date: 2026-05-02 00:00:00.000000
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # pgvector — used in later steps for storing embedded annual-report sections.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # Minimal `runs` table. The orchestrator (step 8) will write a row per
    # analysis request so the WebSocket events can be replayed and the UI
    # can render historical reports at /report/{run_id}.
    op.create_table(
        "runs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("depth", sa.String(length=16), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'queued'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
    )
    op.create_index("ix_runs_ticker", "runs", ["ticker"])
    op.create_index("ix_runs_created_at", "runs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_runs_created_at", table_name="runs")
    op.drop_index("ix_runs_ticker", table_name="runs")
    op.drop_table("runs")
    # We do NOT drop the vector extension on downgrade — other tools in the
    # database may rely on it.
