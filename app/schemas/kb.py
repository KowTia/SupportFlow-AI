"""Pydantic v2 schemas for knowledge base management and RAG search."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.ticket import TicketCategory


class KBArticleCreate(BaseModel):
    """Payload to create or update a knowledge base article."""

    slug: str = Field(min_length=3, max_length=128)
    title: str = Field(min_length=5, max_length=300)
    category: TicketCategory
    content: str = Field(min_length=20, max_length=20000)
    tags: list[str] = Field(default_factory=list)


class KBArticleResponse(BaseModel):
    """Serialized knowledge base article."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    title: str
    category: TicketCategory
    content: str
    tags: list[str]
    created_at: datetime
    updated_at: datetime


class KBArticleListResponse(BaseModel):
    """Paginated listing of knowledge base articles."""

    items: list[KBArticleResponse]
    total: int
    limit: int
    offset: int


class KBSearchRequest(BaseModel):
    """Semantic search query against indexed knowledge base articles."""

    query: str = Field(min_length=2, max_length=2000)
    category: TicketCategory | None = None
    top_k: int = Field(default=3, ge=1, le=20)
    min_score: float = Field(default=0.15, ge=0.0, le=1.0)


class KBSearchHitResponse(BaseModel):
    """Single knowledge base search result with cosine similarity score."""

    article: KBArticleResponse
    score: float


class KBSearchResponse(BaseModel):
    """Semantic search response payload."""

    query: str
    hits: list[KBSearchHitResponse]


class KBSeedResponse(BaseModel):
    """Summary returned after seeding built-in knowledge base articles."""

    created: int
    updated: int
    total: int
