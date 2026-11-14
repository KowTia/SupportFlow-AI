"""Knowledge base article ORM model with cross-dialect vector storage."""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, Enum, String, Text, TypeDecorator, Uuid
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.type_api import TypeEngine

from app.db.base import Base
from app.models.ticket import TicketCategory

EMBEDDING_DIM = 64


class EmbeddingVector(TypeDecorator[list[float]]):
    """Stores embeddings as pgvector Vector(dim) on PostgreSQL and JSON on SQLite."""

    impl = JSON
    cache_ok = True
    comparator_factory = Vector.comparator_factory

    def __init__(self, dim: int = EMBEDDING_DIM) -> None:
        super().__init__()
        self.dim = dim

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[Any]:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(Vector(self.dim))
        return dialect.type_descriptor(JSON())

    def process_bind_param(
        self,
        value: Sequence[float] | None,
        dialect: Dialect,
    ) -> list[float] | None:
        del dialect
        if value is None:
            return None
        return [float(x) for x in value]

    def process_result_value(
        self,
        value: Any,
        dialect: Dialect,
    ) -> list[float] | None:
        del dialect
        if value is None:
            return None
        return [float(x) for x in value]


class KBArticle(Base):
    """Indexed support knowledge base article used for RAG context retrieval."""

    __tablename__ = "kb_articles"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    slug: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    category: Mapped[TicketCategory] = mapped_column(
        Enum(
            TicketCategory,
            native_enum=False,
            create_constraint=False,
            length=64,
            values_callable=lambda cls: [member.value for member in cls],
        ),
        index=True,
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        EmbeddingVector(EMBEDDING_DIM),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
