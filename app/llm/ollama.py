"""Local Ollama /api/chat LLM provider."""

import httpx

from app.llm.base import BaseLLMProvider, LLMProviderError, ProviderReply, post_json_completion


class OllamaProvider(BaseLLMProvider):
    """Async client for local Ollama chat endpoint with JSON format enforcement."""

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.1:8b",
        timeout_seconds: float = 30.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.name = "ollama"
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
        """Request JSON completion from a local Ollama server."""
        data, elapsed_ms = await post_json_completion(
            provider_name=self.name,
            url=f"{self.base_url}/api/chat",
            payload={
                "model": self.model,
                "stream": False,
                "format": "json",
                "options": {"temperature": temperature},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
            timeout_seconds=self.timeout_seconds,
            http_client=self._http_client,
        )

        try:
            content = data["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise LLMProviderError("Ollama response missing message content") from exc

        if not isinstance(content, str) or not content.strip():
            raise LLMProviderError("Ollama response returned empty content")

        return ProviderReply(
            content=content,
            provider=self.name,
            model=self.model,
            latency_ms=elapsed_ms,
        )
