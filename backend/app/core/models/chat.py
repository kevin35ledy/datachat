from __future__ import annotations
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field
import uuid


class ChatMessage(BaseModel):
    """A single message in a chat session."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatSession(BaseModel):
    """A conversation session tied to a database connection."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    connection_id: str
    title: str = "Nouvelle conversation"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class LLMRequest(BaseModel):
    """Input to an LLM provider."""

    messages: list[dict[str, str]]
    temperature: float = 0.1
    max_tokens: int = 1500
    model_override: str | None = None  # Use specific model instead of default


class LLMResponse(BaseModel):
    """Output from an LLM provider."""

    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
