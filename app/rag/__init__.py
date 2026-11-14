"""RAG embeddings, retrieval helpers, and knowledge base seed dataset."""

from app.rag.embeddings import (
    BaseEmbeddingProvider,
    DeterministicHashEmbeddingProvider,
    OllamaEmbeddingProvider,
    OpenAIEmbeddingProvider,
    build_embedding_provider,
    cosine_similarity,
    normalize_vector,
)
from app.rag.seed_data import SEED_KB_ARTICLES

__all__ = [
    "SEED_KB_ARTICLES",
    "BaseEmbeddingProvider",
    "DeterministicHashEmbeddingProvider",
    "OllamaEmbeddingProvider",
    "OpenAIEmbeddingProvider",
    "build_embedding_provider",
    "cosine_similarity",
    "normalize_vector",
]
