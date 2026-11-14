"""Create ticket_analyses table.

Revision ID: 0003_ticket_analyses
Revises: 0002_kb_articles
Create Date: 2026-11-14 20:06:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_ticket_analyses"
down_revision: str | Sequence[str] | None = "0002_kb_articles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ticket_analyses",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("ticket_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("priority", sa.String(length=32), nullable=False),
        sa.Column("assigned_team", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("draft_reply", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("needs_human_review", sa.Boolean(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("cited_kb_ids", sa.JSON(), nullable=False),
        sa.Column("injection_detected", sa.Boolean(), nullable=False),
        sa.Column("injection_risk_score", sa.Float(), nullable=False),
        sa.Column("injection_patterns", sa.JSON(), nullable=False),
        sa.Column("repair_attempts", sa.Integer(), nullable=False),
        sa.Column("fallback_used", sa.Boolean(), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ticket_analyses_ticket_id", "ticket_analyses", ["ticket_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ticket_analyses_ticket_id", table_name="ticket_analyses")
    op.drop_table("ticket_analyses")
