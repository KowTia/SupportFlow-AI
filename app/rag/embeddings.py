"""Embedding providers and vector math utilities for RAG."""

import hashlib
import math
import re
from abc import ABC, abstractmethod
from collections.abc import Sequence

import httpx

from app.core.config import Settings, get_settings
from app.llm.base import LLMProviderError, post_json_completion
from app.models.kb import EMBEDDING_DIM

_TOKEN_RE = re.compile(r"[a-zA-Zа-яА-ЯёЁ0-9]{2,}")

# Bilingual concept anchors mapped into dimensions 0..15 for deterministic offline semantics.
_CONCEPT_ANCHORS: list[tuple[int, tuple[str, ...]]] = [
    (
        0,
        (
            "double",
            "duplicate",
            "twice",
            "charge",
            "charged",
            "card",
            "visa",
            "двойн",
            "дважды",
            "списа",
            "карт",
        ),
    ),
    (1, ("vat", "tax", "invoice", "pdf", "ндс", "счет", "счёт", "налог")),
    (
        2,
        (
            "refund",
            "cancel",
            "proration",
            "subscription",
            "renewal",
            "возврат",
            "отмен",
            "подписк",
        ),
    ),
    (
        3,
        (
            "webhook",
            "hmac",
            "sha256",
            "signature",
            "digest",
            "вебхук",
            "подпис",
        ),
    ),
    (
        4,
        (
            "500",
            "502",
            "504",
            "timeout",
            "latency",
            "gateway",
            "таймаут",
            "ошибк",
            "задерж",
        ),
    ),
    (5, ("rate", "limit", "429", "quota", "retry", "backoff", "лимит", "квот")),
    (
        6,
        (
            "sso",
            "saml",
            "okta",
            "azure",
            "redirect",
            "login",
            "acs",
            "вход",
            "авториз",
        ),
    ),
    (
        7,
        (
            "password",
            "reset",
            "mfa",
            "2fa",
            "locked",
            "authenticator",
            "парол",
            "заблокир",
        ),
    ),
    (
        8,
        (
            "security",
            "leak",
            "exposed",
            "breach",
            "unauthorized",
            "revoke",
            "token",
            "утечк",
            "взлом",
            "несанкц",
            "токен",
            "безопасн",
        ),
    ),
    (
        9,
        (
            "feature",
            "roadmap",
            "csv",
            "export",
            "suggestion",
            "enhancement",
            "фича",
            "предлож",
            "экспорт",
        ),
    ),
    (10, ("billing", "payment", "оплат", "платеж")),
    (11, ("api", "error", "integration", "интеграц")),
    (12, ("account", "workspace", "member", "аккаунт")),
]

_ANCHOR_DIM_COUNT = 16


def normalize_vector(values: Sequence[float], dim: int = EMBEDDING_DIM) -> list[float]:
    """Resize/truncate vector to target dimension and L2-normalize to unit length."""
    if dim <= 0:
        raise ValueError("Embedding dimension must be positive")

    resized = [float(values[i]) if i < len(values) else 0.0 for i in range(dim)]
    norm = math.sqrt(sum(v * v for v in resized))
    if norm == 0.0:
        uniform = 1.0 / math.sqrt(dim)
        return [uniform] * dim
    return [v / norm for v in resized]


def cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
    """Compute cosine similarity in [-1.0, 1.0] between two vectors."""
    length = min(len(vec_a), len(vec_b))
    if length == 0:
        return 0.0
    dot = sum(vec_a[i] * vec_b[i] for i in range(length))
    norm_a = math.sqrt(sum(vec_a[i] * vec_a[i] for i in range(length)))
    norm_b = math.sqrt(sum(vec_b[i] * vec_b[i] for i in range(length)))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class BaseEmbeddingProvider(ABC):
    """Contract for generating fixed-dimension text embeddings."""

    name: str
    dimension: int = EMBEDDING_DIM

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        """Convert input text into a normalized embedding vector."""


class DeterministicHashEmbeddingProvider(BaseEmbeddingProvider):
    """Offline deterministic bilingual embedding provider using anchors + feature hashing."""

    def __init__(self, dimension: int = EMBEDDING_DIM) -> None:
        if dimension <= _ANCHOR_DIM_COUNT:
            raise ValueError(f"dimension must be greater than {_ANCHOR_DIM_COUNT}")
        self.name = "hash"
        self.dimension = dimension

    async def embed_text(self, text: str) -> list[float]:
        """Compute deterministic normalized embedding vector for text."""
        vec = [0.0] * self.dimension
        lower = text.lower()

        for dim_idx, keywords in _CONCEPT_ANCHORS:
            hits = sum(1 for kw in keywords if kw in lower)
            if hits > 0:
                vec[dim_idx] += 2.0 * hits

        hash_span = self.dimension - _ANCHOR_DIM_COUNT
        tokens = _TOKEN_RE.findall(lower)
        for token in tokens:
            features = [token]
            if len(token) >= 4:
                features.append(token[:4])
            for feat in features:
                digest = hashlib.sha256(feat.encode("utf-8")).digest()
                bucket = _ANCHOR_DIM_COUNT + (int.from_bytes(digest[:4], "big") % hash_span)
                sign = 1.0 if (digest[4] & 1) == 0 else -1.0
                weight = 0.6 if feat == token else 0.35
                vec[bucket] += sign * weight

        return normalize_vector(vec, dim=self.dimension)


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI-compatible /embeddings client."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "text-embedding-3-small",
        dimension: int = EMBEDDING_DIM,
        timeout_seconds: float = 30.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.name = "openai"
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.dimension = dimension
        self.timeout_seconds = timeout_seconds
        self._http_client = http_client

    async def embed_text(self, text: str) -> list[float]:
        if not self.api_key.strip():
            raise LLMProviderError("OpenAI API key is not configured for embeddings")

        data, _ = await post_json_completion(
            provider_name=f"{self.name}-embeddings",
            url=f"{self.base_url}/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}"},
            payload={
                "model": self.model,
                "input": text,
                "dimensions": self.dimension,
            },
            timeout_seconds=self.timeout_seconds,
            http_client=self._http_client,
        )
        try:
            raw_vec = data["data"][0]["embedding"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMProviderError("OpenAI embeddings response missing embedding vector") from exc

        return normalize_vector(raw_vec, dim=self.dimension)


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    """Local Ollama /api/embeddings client."""

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
        dimension: int = EMBEDDING_DIM,
        timeout_seconds: float = 30.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.name = "ollama"
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.dimension = dimension
        self.timeout_seconds = timeout_seconds
        self._http_client = http_client

    async def embed_text(self, text: str) -> list[float]:
        data, _ = await post_json_completion(
            provider_name=f"{self.name}-embeddings",
            url=f"{self.base_url}/api/embeddings",
            payload={"model": self.model, "prompt": text},
            timeout_seconds=self.timeout_seconds,
            http_client=self._http_client,
        )
        raw_vec = data.get("embedding")
        if not isinstance(raw_vec, list) or not raw_vec:
            raise LLMProviderError("Ollama embeddings response missing embedding vector")

        return normalize_vector(raw_vec, dim=self.dimension)


def build_embedding_provider(settings: Settings | None = None) -> BaseEmbeddingProvider:
    """Instantiate configured embedding provider."""
    cfg = settings or get_settings()
    name = cfg.embedding_provider.strip().lower()
    if name == "hash":
        return DeterministicHashEmbeddingProvider(dimension=cfg.embedding_dim)
    if name == "openai":
        return OpenAIEmbeddingProvider(
            api_key=cfg.openai_api_key,
            base_url=cfg.openai_base_url,
            dimension=cfg.embedding_dim,
            timeout_seconds=cfg.llm_timeout_seconds,
        )
    if name == "ollama":
        return OllamaEmbeddingProvider(
            base_url=cfg.ollama_base_url,
            dimension=cfg.embedding_dim,
            timeout_seconds=cfg.llm_timeout_seconds,
        )
    raise ValueError(f"Unsupported embedding provider: {cfg.embedding_provider}")
