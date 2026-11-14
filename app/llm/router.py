"""Hybrid LLM router with primary and fallback provider execution."""

from app.core.config import Settings, get_settings
from app.llm.base import BaseLLMProvider, LLMProviderError, ProviderReply
from app.llm.mock import MockLLMProvider
from app.llm.ollama import OllamaProvider
from app.llm.openai_compat import OpenAICompatibleProvider


class HybridLLMRouter:
    """Routes completion calls to a primary provider with automatic fallback on failure."""

    def __init__(
        self,
        primary: BaseLLMProvider,
        fallback: BaseLLMProvider | None = None,
    ) -> None:
        self.primary = primary
        self.fallback = fallback

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
    ) -> tuple[ProviderReply, bool]:
        """Generate completion from primary provider, falling back on LLMProviderError."""
        try:
            reply = await self.primary.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
            )
            return reply, False
        except LLMProviderError:
            if self.fallback is not None and self.fallback is not self.primary:
                reply = await self.fallback.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                )
                return reply, True
            raise


def build_provider(name: str, settings: Settings) -> BaseLLMProvider:
    """Instantiate a concrete LLM provider by configured name."""
    normalized = name.strip().lower()
    if normalized == "mock":
        return MockLLMProvider()
    if normalized == "openai":
        return OpenAICompatibleProvider(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.openai_model,
            timeout_seconds=settings.llm_timeout_seconds,
        )
    if normalized == "ollama":
        return OllamaProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout_seconds=settings.llm_timeout_seconds,
        )
    raise ValueError(f"Unsupported LLM provider: {name}")


def build_llm_router(settings: Settings | None = None) -> HybridLLMRouter:
    """Build a HybridLLMRouter configured from application settings."""
    cfg = settings or get_settings()
    primary = build_provider(cfg.llm_provider, cfg)

    fallback_name = cfg.llm_fallback_provider.strip().lower()
    primary_name = cfg.llm_provider.strip().lower()
    fallback = (
        build_provider(fallback_name, cfg)
        if fallback_name and fallback_name != primary_name
        else None
    )
    return HybridLLMRouter(primary=primary, fallback=fallback)
