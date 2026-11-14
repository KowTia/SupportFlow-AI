"""Create kb_articles table with pgvector embedding column and HNSW index.

Revision ID: 0002_kb_articles
Revises: 0001_initial
Create Date: 2026-11-14 19:57:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0002_kb_articles"
down_revision: str | Sequence[str] | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIM = 64


def upgrade() -> None:
    dialect_name = op.get_bind().dialect.name
    embedding_type: sa.types.TypeEngine[object] = (
        Vector(EMBEDDING_DIM) if dialect_name == "postgresql" else sa.JSON()
    )

    op.create_table(
        "kb_articles",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("embedding", embedding_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_kb_articles_slug", "kb_articles", ["slug"], unique=True)
    op.create_index("ix_kb_articles_category", "kb_articles", ["category"], unique=False)

    if dialect_name == "postgresql":
        op.execute(
            "CREATE INDEX ix_kb_articles_embedding_hnsw "
            "ON kb_articles USING hnsw (embedding vector_cosine_ops)"
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.drop_index("ix_kb_articles_embedding_hnsw", table_name="kb_articles")

    op.drop_index("ix_kb_articles_category", table_name="kb_articles")
    op.drop_index("ix_kb_articles_slug", table_name="kb_articles")
    op.drop_table("kb_articles")
