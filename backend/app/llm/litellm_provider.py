from __future__ import annotations
from typing import TYPE_CHECKING
from app.llm.base import BaseLLMProvider

if TYPE_CHECKING:
    from app.config import Settings


class LiteLLMProvider(BaseLLMProvider):
    """Generic LiteLLM provider — used as fallback for any model string."""

    def __init__(self, settings: "Settings", model: str):
        super().__init__(settings, model=model)
