"""Base interface, shared HTTP helper, and exceptions for LLM providers."""

import time
from abc import ABC, abstractmethod
from typing import Any

import httpx
from pydantic import BaseModel


class LLMProviderError(Exception):
    """Raised when an LLM provider fails to produce a response."""


class LLMRepairExhaustedError(LLMProviderError):
    """Raised when structured output validation fails after all repair retries."""

    def __init__(self, *, attempts: int, last_raw_output: str, last_error: str) -> None:
        self.attempts = attempts
        self.last_raw_output = last_raw_output
        self.last_error = last_error
        super().__init__(
            f"Failed to produce valid analysis JSON after {attempts} attempts: {last_error}"
        )


class ProviderReply(BaseModel):
    """Raw completion returned by an LLM provider."""

    content: str
    provider: str
    model: str
    latency_ms: float = 0.0


class BaseLLMProvider(ABC):
    """Abstract contract shared by all LLM providers."""

    name: str
    model: str

    @abstractmethod
    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
    ) -> ProviderReply:
        """Generate a raw completion string for the given prompts."""


async def post_json_completion(
    *,
    provider_name: str,
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str] | None = None,
    timeout_seconds: float = 30.0,
    http_client: httpx.AsyncClient | None = None,
) -> tuple[dict[str, Any], float]:
    """Execute a JSON POST request to an LLM HTTP endpoint and return parsed JSON + latency."""
    start = time.perf_counter()
    try:
        if http_client is not None:
            response = await http_client.post(
                url,
                json=payload,
                headers=headers,
                timeout=timeout_seconds,
            )
        else:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(url, json=payload, headers=headers)
    except httpx.HTTPError as exc:
        raise LLMProviderError(f"{provider_name} request failed: {exc}") from exc

    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    if response.status_code >= 400:
        raise LLMProviderError(
            f"{provider_name} returned HTTP {response.status_code}: {response.text[:300]}"
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise LLMProviderError(f"{provider_name} returned non-JSON response") from exc

    if not isinstance(data, dict):
        raise LLMProviderError(f"{provider_name} returned unexpected JSON root type")

    return data, elapsed_ms
