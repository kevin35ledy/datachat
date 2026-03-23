from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime
from typing import TYPE_CHECKING
from app.core.models.query import QueryHistoryEntry
import uuid

if TYPE_CHECKING:
    from app.config import Settings


class QueryRepository:
    """Stores query history as JSONL files per connection. Phase 1 implementation."""

    def __init__(self, settings: "Settings"):
        self._store_dir = Path(".datachat_history")
        self._store_dir.mkdir(exist_ok=True)

    def _path(self, connection_id: str) -> Path:
        return self._store_dir / f"{connection_id}.jsonl"

    async def save(
        self,
        connection_id: str,
        session_id: str,
        nl_text: str,
        sql_text: str,
        row_count: int,
        execution_time_ms: int,
    ) -> QueryHistoryEntry:
        entry = QueryHistoryEntry(
            id=str(uuid.uuid4()),
            connection_id=connection_id,
            session_id=session_id,
            nl_text=nl_text,
            sql_text=sql_text,
            row_count=row_count,
            execution_time_ms=execution_time_ms,
        )
        with self._path(connection_id).open("a") as f:
            f.write(json.dumps(entry.model_dump(mode="json")) + "\n")
        return entry

    async def list_by_connection(
        self, connection_id: str, limit: int = 50
    ) -> list[QueryHistoryEntry]:
        path = self._path(connection_id)
        if not path.exists():
            return []
        entries = []
        with path.open() as f:
            for line in f:
                try:
                    entries.append(QueryHistoryEntry(**json.loads(line)))
                except Exception:
                    continue
        return list(reversed(entries[-limit:]))
