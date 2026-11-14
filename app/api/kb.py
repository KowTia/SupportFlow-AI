"""Knowledge base management and semantic RAG search endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.ticket import TicketCategory
from app.schemas.kb import (
    KBArticleCreate,
    KBArticleListResponse,
    KBArticleResponse,
    KBSearchHitResponse,
    KBSearchRequest,
    KBSearchResponse,
    KBSeedResponse,
)
from app.services.kb import (
    delete_kb_article,
    get_kb_article_by_id,
    list_kb_articles,
    search_kb_articles,
    seed_kb_articles,
    upsert_kb_article,
)

router = APIRouter(prefix="/kb", tags=["knowledge-base"])


@router.get("", response_model=KBArticleListResponse)
async def list_kb_articles_endpoint(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    category: TicketCategory | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> KBArticleListResponse:
    """List indexed knowledge base articles with optional category filtering."""
    items, total = await list_kb_articles(
        session,
        category=category,
        limit=limit,
        offset=offset,
    )
    return KBArticleListResponse(
        items=[KBArticleResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=KBArticleResponse, status_code=status.HTTP_201_CREATED)
async def upsert_kb_article_endpoint(
    payload: KBArticleCreate,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> KBArticleResponse:
    """Create or update a knowledge base article and index its embedding."""
    article, created = await upsert_kb_article(session, payload)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return KBArticleResponse.model_validate(article)


@router.post("/seed", response_model=KBSeedResponse)
async def seed_kb_endpoint(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> KBSeedResponse:
    """Idempotently load built-in knowledge base articles into the vector store."""
    created, updated, total = await seed_kb_articles(session)
    return KBSeedResponse(created=created, updated=updated, total=total)


@router.post("/search", response_model=KBSearchResponse)
async def search_kb_endpoint(
    payload: KBSearchRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> KBSearchResponse:
    """Perform semantic RAG search across indexed knowledge base articles."""
    hits = await search_kb_articles(
        session,
        payload.query,
        category=payload.category,
        top_k=payload.top_k,
        min_score=payload.min_score,
    )
    return KBSearchResponse(
        query=payload.query,
        hits=[
            KBSearchHitResponse(
                article=KBArticleResponse.model_validate(article),
                score=score,
            )
            for article, score in hits
        ],
    )


@router.get("/{article_id}", response_model=KBArticleResponse)
async def get_kb_article_endpoint(
    article_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> KBArticleResponse:
    """Retrieve a single knowledge base article by UUID."""
    article = await get_kb_article_by_id(session, article_id)
    if article is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base article not found",
        )
    return KBArticleResponse.model_validate(article)


@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_kb_article_endpoint(
    article_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    """Delete a knowledge base article by UUID."""
    article = await get_kb_article_by_id(session, article_id)
    if article is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base article not found",
        )
    await delete_kb_article(session, article)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
