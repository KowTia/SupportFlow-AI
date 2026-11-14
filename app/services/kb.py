"""Knowledge base CRUD, seed, and pgvector/SQLite RAG retrieval services."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.kb import KBArticle
from app.models.ticket import TicketCategory
from app.rag.embeddings import BaseEmbeddingProvider, build_embedding_provider, cosine_similarity
from app.rag.seed_data import SEED_KB_ARTICLES
from app.schemas.kb import KBArticleCreate


def _build_article_index_text(payload: KBArticleCreate) -> str:
    """Combine article title, tags, and body into embedding source text."""
    return f"{payload.title.strip()}\n{' '.join(payload.tags)}\n{payload.content.strip()}"


async def upsert_kb_article(
    session: AsyncSession,
    payload: KBArticleCreate,
    embedding_provider: BaseEmbeddingProvider | None = None,
) -> tuple[KBArticle, bool]:
    """Create or update a knowledge base article by unique slug and index its embedding."""
    provider = embedding_provider or build_embedding_provider()
    normalized_slug = payload.slug.strip()
    normalized_tags = [tag.strip() for tag in payload.tags if tag.strip()]
    embedding = await provider.embed_text(_build_article_index_text(payload))

    existing = await session.scalar(select(KBArticle).where(KBArticle.slug == normalized_slug))
    if existing is not None:
        existing.title = payload.title.strip()
        existing.category = payload.category
        existing.content = payload.content.strip()
        existing.tags = normalized_tags
        existing.embedding = embedding
        existing.updated_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(existing)
        return existing, False

    article = KBArticle(
        slug=normalized_slug,
        title=payload.title.strip(),
        category=payload.category,
        content=payload.content.strip(),
        tags=normalized_tags,
        embedding=embedding,
    )
    session.add(article)
    await session.commit()
    await session.refresh(article)
    return article, True


async def seed_kb_articles(
    session: AsyncSession,
    embedding_provider: BaseEmbeddingProvider | None = None,
) -> tuple[int, int, int]:
    """Idempotently upsert all built-in seed knowledge base articles."""
    provider = embedding_provider or build_embedding_provider()
    created_count = 0
    updated_count = 0

    for item in SEED_KB_ARTICLES:
        payload = KBArticleCreate.model_validate(item)
        _, created = await upsert_kb_article(session, payload, embedding_provider=provider)
        if created:
            created_count += 1
        else:
            updated_count += 1

    return created_count, updated_count, len(SEED_KB_ARTICLES)


async def list_kb_articles(
    session: AsyncSession,
    *,
    category: TicketCategory | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[KBArticle], int]:
    """Return paginated knowledge base articles optionally filtered by category."""
    count_stmt = select(func.count()).select_from(KBArticle)
    data_stmt = select(KBArticle).order_by(KBArticle.created_at.desc())

    if category is not None:
        count_stmt = count_stmt.where(KBArticle.category == category)
        data_stmt = data_stmt.where(KBArticle.category == category)

    total = await session.scalar(count_stmt) or 0
    rows = await session.scalars(data_stmt.offset(offset).limit(limit))
    return list(rows.all()), int(total)


async def get_kb_article_by_id(session: AsyncSession, article_id: uuid.UUID) -> KBArticle | None:
    """Fetch a knowledge base article by UUID."""
    return await session.scalar(select(KBArticle).where(KBArticle.id == article_id))


async def delete_kb_article(session: AsyncSession, article: KBArticle) -> None:
    """Delete a knowledge base article."""
    await session.delete(article)
    await session.commit()


async def search_kb_articles(
    session: AsyncSession,
    query: str,
    *,
    category: TicketCategory | None = None,
    top_k: int | None = None,
    min_score: float | None = None,
    embedding_provider: BaseEmbeddingProvider | None = None,
) -> list[tuple[KBArticle, float]]:
    """Retrieve top-K semantically similar knowledge base articles with cosine scores."""
    settings = get_settings()
    resolved_top_k = settings.rag_top_k if top_k is None else top_k
    resolved_min_score = settings.rag_min_score if min_score is None else min_score

    provider = embedding_provider or build_embedding_provider(settings)
    query_vec = await provider.embed_text(query)

    bind = session.get_bind()
    dialect_name = bind.dialect.name if bind is not None else "sqlite"

    if dialect_name == "postgresql":
        distance_expr = KBArticle.embedding.cosine_distance(query_vec)
        stmt = select(KBArticle, distance_expr.label("distance"))
        if category is not None:
            stmt = stmt.where(KBArticle.category == category)
        stmt = stmt.order_by(distance_expr.asc()).limit(resolved_top_k)

        rows = (await session.execute(stmt)).all()
        hits: list[tuple[KBArticle, float]] = []
        for article, distance in rows:
            score = max(-1.0, min(1.0, 1.0 - float(distance)))
            if score >= resolved_min_score:
                hits.append((article, round(score, 4)))
        return hits

    stmt = select(KBArticle)
    if category is not None:
        stmt = stmt.where(KBArticle.category == category)
    candidates = list((await session.scalars(stmt)).all())

    scored: list[tuple[KBArticle, float]] = []
    for article in candidates:
        score = cosine_similarity(query_vec, article.embedding)
        if score >= resolved_min_score:
            scored.append((article, round(score, 4)))

    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:resolved_top_k]


async def retrieve_kb_context_for_ticket(
    session: AsyncSession,
    *,
    subject: str,
    body: str,
    top_k: int | None = None,
    min_score: float | None = None,
    embedding_provider: BaseEmbeddingProvider | None = None,
) -> list[dict[str, str]]:
    """Format top-K RAG knowledge base hits as context dictionaries for TicketAnalyzer."""
    hits = await search_kb_articles(
        session,
        f"{subject.strip()}\n{body.strip()}",
        top_k=top_k,
        min_score=min_score,
        embedding_provider=embedding_provider,
    )
    return [
        {
            "id": article.slug,
            "title": article.title,
            "content": article.content,
            "category": str(article.category),
            "score": f"{score:.4f}",
        }
        for article, score in hits
    ]
