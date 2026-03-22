from __future__ import annotations
import os
from typing import TYPE_CHECKING
from app.llm.base import BaseLLMProvider

if TYPE_CHECKING:
    from app.config import Settings


class AnthropicProvider(BaseLLMProvider):
    """
    LLM provider for Anthropic Claude models via LiteLLM.

    Required env vars:
        ANTHROPIC_API_KEY

    Recommended models:
        - claude-sonnet-4-6       : default, best quality/speed balance
        - claude-opus-4-6         : highest quality, for complex audit analysis
        - claude-haiku-4-5-20251001 : fastest, for summaries and classification
    """

    def __init__(self, settings: "Settings", model_override: str | None = None):
        model = model_override or settings.litellm_default_model
        if not model.startswith("claude"):
            model = "claude-sonnet-4-6"
        super().__init__(settings, model=model)
        # Ensure LiteLLM picks up the API key
        os.environ.setdefault("ANTHROPIC_API_KEY", settings.anthropic_api_key)
