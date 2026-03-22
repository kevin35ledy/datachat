from __future__ import annotations
import time
from typing import AsyncIterator, TYPE_CHECKING
from app.core.models.chat import LLMRequest, LLMResponse

if TYPE_CHECKING:
    from app.config import Settings


class BaseLLMProvider:
    """
    Base class for all LLM providers.
    Uses LiteLLM as the unified underlying API.
    Override complete() and stream() for provider-specific behavior if needed.
    """

    def __init__(self, settings: "Settings", model: str | None = None):
        self._settings = settings
        self._model = model or settings.litellm_default_model

    async def complete(self, request: LLMRequest) -> LLMResponse:
        import litellm
        start = time.monotonic()
        model = request.model_override or self._model
        kwargs: dict = dict(
            model=model,
            messages=request.messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        if model.startswith("ollama/"):
            kwargs["api_base"] = self._settings.ollama_api_base
        response = await litellm.acompletion(**kwargs)
        elapsed_ms = int((time.monotonic() - start) * 1000)
        usage = response.usage or {}
        return LLMResponse(
            content=response.choices[0].message.content or "",
            model=model,
            input_tokens=getattr(usage, "prompt_tokens", 0),
            output_tokens=getattr(usage, "completion_tokens", 0),
            latency_ms=elapsed_ms,
        )

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        import litellm
        model = request.model_override or self._model
        kwargs: dict = dict(
            model=model,
            messages=request.messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=True,
        )
        if model.startswith("ollama/"):
            kwargs["api_base"] = self._settings.ollama_api_base
        response = await litellm.acompletion(**kwargs)
        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content

    async def embed(self, text: str) -> list[float]:
        import litellm
        # Use a fast embedding model — fall back to anthropic's via OpenAI-compatible API
        embed_model = "text-embedding-3-small"
        response = await litellm.aembedding(model=embed_model, input=[text])
        return response.data[0]["embedding"]

    def count_tokens(self, text: str) -> int:
        try:
            import litellm
            return litellm.token_counter(model=self._model, text=text)
        except Exception:
            return len(text) // 4  # rough fallback

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def max_context_tokens(self) -> int:
        # Conservative defaults by model family
        if "opus" in self._model:
            return 180_000
        if "sonnet" in self._model:
            return 180_000
        if "haiku" in self._model:
            return 180_000
        if "gpt-4o" in self._model:
            return 128_000
        return 32_000

    @property
    def supports_streaming(self) -> bool:
        return True
