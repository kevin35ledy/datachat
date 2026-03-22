from __future__ import annotations
import os
from typing import TYPE_CHECKING
from app.llm.base import BaseLLMProvider

if TYPE_CHECKING:
    from app.config import Settings


class OpenAIProvider(BaseLLMProvider):
    """
    LLM provider for OpenAI GPT models via LiteLLM.

    Required env vars:
        OPENAI_API_KEY

    Recommended models:
        - gpt-4o       : best quality
        - gpt-4o-mini  : faster and cheaper
    """

    def __init__(self, settings: "Settings", model_override: str | None = None):
        model = model_override or "gpt-4o"
        super().__init__(settings, model=model)
        os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)
