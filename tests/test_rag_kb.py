"""Tests for RAG embeddings, pgvector/SQLite KB search, seed idempotency, and analyzer wiring."""

import math
import uuid

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm import HybridLLMRouter, LLMProviderError, MockLLMProvider, TicketAnalyzer
from app.rag import (
    DeterministicHashEmbeddingProvider,
    OllamaEmbeddingProvider,
    OpenAIEmbeddingProvider,
    cosine_similarity,
)
from app.services.kb import retrieve_kb_context_for_ticket


async def test_hash_embedding_provider_unit_norm_and_semantic_ranking() -> None:
    provider = DeterministicHashEmbeddingProvider()
    vec_billing = await provider.embed_text(
        "Double charge on my Visa card for monthly subscription"
    )
    vec_article_billing = await provider.embed_text(
        "Handling duplicate card charges and billing refunds for double payments"
    )
    vec_article_sso = await provider.embed_text(
        "Resolving SAML SSO login redirect loops in Okta and Azure AD"
    )

    assert len(vec_billing) == 64
    norm = math.sqrt(sum(v * v for v in vec_billing))
    assert norm == pytest.approx(1.0, abs=1e-6)

    sim_billing = cosine_similarity(vec_billing, vec_article_billing)
    sim_sso = cosine_similarity(vec_billing, vec_article_sso)
    assert sim_billing > sim_sso


async def test_openai_and_ollama_embedding_providers_with_mock_transport() -> None:
    def openai_handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://api.example.com/v1/embeddings"
        return httpx.Response(200, json={"data": [{"embedding": [3.0, 4.0] + [0.0] * 62}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(openai_handler)) as client:
        openai_emb = OpenAIEmbeddingProvider(
            api_key="sk-test",
            base_url="https://api.example.com/v1",
            http_client=client,
        )
        vec = await openai_emb.embed_text("hello")
        assert len(vec) == 64
        assert vec[0] == pytest.approx(0.6, abs=1e-6)
        assert vec[1] == pytest.approx(0.8, abs=1e-6)

    no_key = OpenAIEmbeddingProvider(api_key="")
    with pytest.raises(LLMProviderError, match="API key"):
        await no_key.embed_text("hello")

    def ollama_handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "http://ollama.local:11434/api/embeddings"
        return httpx.Response(200, json={"embedding": [1.0] * 64})

    async with httpx.AsyncClient(transport=httpx.MockTransport(ollama_handler)) as client:
        ollama_emb = OllamaEmbeddingProvider(
            base_url="http://ollama.local:11434",
            http_client=client,
        )
        vec = await ollama_emb.embed_text("hello")
        assert len(vec) == 64
        assert math.sqrt(sum(v * v for v in vec)) == pytest.approx(1.0, abs=1e-6)


async def test_kb_seed_is_idempotent(client: httpx.AsyncClient) -> None:
    first = await client.post("/api/v1/kb/seed")
    assert first.status_code == 200
    assert first.json() == {"created": 10, "updated": 0, "total": 10}

    second = await client.post("/api/v1/kb/seed")
    assert second.status_code == 200
    assert second.json() == {"created": 0, "updated": 10, "total": 10}

    listing = await client.get("/api/v1/kb")
    assert listing.status_code == 200
    assert listing.json()["total"] == 10


@pytest.mark.parametrize(
    ("query", "expected_slug"),
    [
        (
            "My card was charged twice for the same invoice",
            "billing-duplicate-charge-refund",
        ),
        (
            "Webhook HMAC SHA-256 signature verification fails on retry",
            "technical-webhook-hmac-verification",
        ),
        (
            "Okta SAML SSO keeps redirecting back to login screen",
            "account-sso-saml-redirect-loop",
        ),
        (
            "Несанкционированный доступ и утечка API токена в репозитории",
            "security-compromised-api-token-response",
        ),
    ],
)
async def test_kb_search_ranks_relevant_article_first(
    client: httpx.AsyncClient,
    query: str,
    expected_slug: str,
) -> None:
    await client.post("/api/v1/kb/seed")

    resp = await client.post(
        "/api/v1/kb/search",
        json={"query": query, "top_k": 3, "min_score": 0.1},
    )
    assert resp.status_code == 200
    hits = resp.json()["hits"]
    assert len(hits) >= 1
    assert hits[0]["article"]["slug"] == expected_slug
    assert hits[0]["score"] >= 0.3

    filtered = await client.post(
        "/api/v1/kb/search",
        json={
            "query": query,
            "category": "feature_request",
            "top_k": 3,
            "min_score": 0.99,
        },
    )
    assert filtered.status_code == 200
    assert filtered.json()["hits"] == []


async def test_kb_crud_upsert_list_get_delete_and_404(client: httpx.AsyncClient) -> None:
    create_payload = {
        "slug": "custom-sdk-retry-policy",
        "title": "SDK Retry Policy and Exponential Backoff Guide",
        "category": "technical",
        "content": "Configure client retries with jittered backoff for transient HTTP 503.",
        "tags": ["sdk", "retry", "503"],
    }
    created = await client.post("/api/v1/kb", json=create_payload)
    assert created.status_code == 201
    article_id = created.json()["id"]

    updated = await client.post(
        "/api/v1/kb",
        json={**create_payload, "title": "Updated SDK Retry Policy Guide"},
    )
    assert updated.status_code == 200
    assert updated.json()["id"] == article_id
    assert updated.json()["title"] == "Updated SDK Retry Policy Guide"

    listing = await client.get("/api/v1/kb", params={"category": "technical"})
    assert listing.status_code == 200
    assert listing.json()["total"] == 1

    fetched = await client.get(f"/api/v1/kb/{article_id}")
    assert fetched.status_code == 200
    assert fetched.json()["slug"] == "custom-sdk-retry-policy"

    deleted = await client.delete(f"/api/v1/kb/{article_id}")
    assert deleted.status_code == 204
    assert (await client.get(f"/api/v1/kb/{article_id}")).status_code == 404

    unknown_id = str(uuid.uuid4())
    assert (await client.get(f"/api/v1/kb/{unknown_id}")).status_code == 404
    assert (await client.delete(f"/api/v1/kb/{unknown_id}")).status_code == 404


async def test_rag_context_integrates_with_ticket_analyzer(
    client: httpx.AsyncClient,
    db_session: AsyncSession,
) -> None:
    await client.post("/api/v1/kb/seed")

    kb_context = await retrieve_kb_context_for_ticket(
        db_session,
        subject="Webhook HMAC SHA-256 verification fails",
        body="Our receiver rejects X-SupportFlow-Signature on retried webhook deliveries.",
        top_k=2,
        min_score=0.2,
    )
    assert len(kb_context) >= 1
    assert kb_context[0]["id"] == "technical-webhook-hmac-verification"

    analyzer = TicketAnalyzer(HybridLLMRouter(primary=MockLLMProvider()))
    bundle = await analyzer.analyze(
        subject="Webhook HMAC SHA-256 verification fails",
        body="Our receiver rejects X-SupportFlow-Signature on retried webhook deliveries.",
        kb_context=kb_context,
    )
    assert "technical-webhook-hmac-verification" in bundle.analysis.cited_kb_ids
