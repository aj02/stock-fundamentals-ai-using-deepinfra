"""runs.report JSONB column for persisted RunReport

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-02 00:00:00.000000
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Persisted assembled RunReport. JSONB so we can index keys later if we
    # ever need to (e.g. by ticker, by status) without schema changes.
    op.add_column("runs", sa.Column("report", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("runs", "report")
