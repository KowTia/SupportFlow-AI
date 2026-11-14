"""OpenAI-compatible Chat Completions LLM provider."""

import httpx

from app.llm.base import BaseLLMProvider, LLMProviderError, ProviderReply, post_json_completion


class OpenAICompatibleProvider(BaseLLMProvider):
    """Async client for OpenAI and OpenAI-compatible /chat/completions APIs."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        timeout_seconds: float = 30.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.name = "openai"
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._http_client = http_client

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
    ) -> ProviderReply:
        """Request JSON-mode chat completion from an OpenAI-compatible endpoint."""
        if not self.api_key.strip():
            raise LLMProviderError("OpenAI API key is not configured")

        data, elapsed_ms = await post_json_completion(
            provider_name=self.name,
            url=f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            payload={
                "model": self.model,
                "temperature": temperature,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
            timeout_seconds=self.timeout_seconds,
            http_client=self._http_client,
        )

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMProviderError("OpenAI-compatible response missing message content") from exc

        if not isinstance(content, str) or not content.strip():
            raise LLMProviderError("OpenAI-compatible response returned empty content")

        return ProviderReply(
            content=content,
            provider=self.name,
            model=self.model,
            latency_ms=elapsed_ms,
        )
