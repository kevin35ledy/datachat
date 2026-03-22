from __future__ import annotations
from typing import AsyncIterator, Protocol, runtime_checkable


@runtime_checkable
class AbstractLLMProvider(Protocol):
    """
    Protocol that every LLM provider must satisfy.

    Implementations live in app/llm/. Register them in app/llm/registry.py.
    See docs/guides/add-llm-provider.md for the step-by-step guide.
    """

    async def complete(self, request: "LLMRequest") -> "LLMResponse":
        """Non-streaming completion. Returns the full response at once."""
        ...

    async def stream(self, request: "LLMRequest") -> AsyncIterator[str]:
        """Streaming completion. Yields tokens as they are generated."""
        ...

    async def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for RAG use (schema retrieval)."""
        ...

    def count_tokens(self, text: str) -> int:
        """Estimate token count for prompt budget management."""
        ...

    @property
    def model_name(self) -> str:
        """The model identifier string used in API calls."""
        ...

    @property
    def max_context_tokens(self) -> int:
        """Maximum context window size for this model."""
        ...

    @property
    def supports_streaming(self) -> bool:
        """Whether this provider supports token-level streaming."""
        ...


from app.core.models.chat import LLMRequest, LLMResponse  # noqa: E402
