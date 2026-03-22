from __future__ import annotations
# Chat session management — Phase 1 stub
# Full implementation (persistent sessions, context management) in Phase 2.

from app.core.models.chat import ChatSession, ChatMessage
import uuid
from datetime import datetime


class ChatService:
    """Manages chat sessions and message history (in-memory for Phase 1)."""

    _sessions: dict[str, ChatSession] = {}
    _history: dict[str, list[ChatMessage]] = {}

    def get_or_create_session(self, session_id: str, connection_id: str) -> ChatSession:
        if session_id not in self._sessions:
            self._sessions[session_id] = ChatSession(
                id=session_id,
                connection_id=connection_id,
            )
        return self._sessions[session_id]

    def get_history(self, session_id: str) -> list[ChatMessage]:
        return self._history.get(session_id, [])

    def add_message(self, message: ChatMessage) -> None:
        if message.session_id not in self._history:
            self._history[message.session_id] = []
        self._history[message.session_id].append(message)
        # Keep last 20 messages per session
        self._history[message.session_id] = self._history[message.session_id][-20:]
