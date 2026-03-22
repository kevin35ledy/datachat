from __future__ import annotations
from typing import TYPE_CHECKING
from app.core.exceptions import LLMProviderNotFoundError
from app.core.interfaces.llm_provider import AbstractLLMProvider

if TYPE_CHECKING:
    from app.config import Settings


class LLMRegistry:
    """Maps provider names to LLM provider implementations."""

    def __init__(self, settings: "Settings"):
        self._settings = settings
        self._default: AbstractLLMProvider | None = None

    def get_default(self) -> AbstractLLMProvider:
        if self._default is None:
            self._default = self._build_default()
        return self._default

    def get_by_name(self, provider: str, model: str | None = None) -> AbstractLLMProvider:
        from app.llm.anthropic_provider import AnthropicProvider
        from app.llm.openai_provider import OpenAIProvider

        registry_map = {
            "anthropic": AnthropicProvider,
            "claude": AnthropicProvider,
            "openai": OpenAIProvider,
            "gpt": OpenAIProvider,
        }
        cls = registry_map.get(provider.lower())
        if cls is None:
            raise LLMProviderNotFoundError(
                f"No LLM provider registered for '{provider}'. "
                f"Supported: {list(registry_map.keys())}"
            )
        return cls(settings=self._settings, model_override=model)

    def _build_default(self) -> AbstractLLMProvider:
        model = self._settings.litellm_default_model
        if "claude" in model or "anthropic" in model:
            from app.llm.anthropic_provider import AnthropicProvider
            return AnthropicProvider(settings=self._settings)
        if "gpt" in model or "openai" in model:
            from app.llm.openai_provider import OpenAIProvider
            return OpenAIProvider(settings=self._settings)
        # Fallback — use generic LiteLLM wrapper
        from app.llm.litellm_provider import LiteLLMProvider
        return LiteLLMProvider(settings=self._settings, model=model)
