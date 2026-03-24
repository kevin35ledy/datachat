from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING
from app.core.models.annotations import SchemaAnnotations

if TYPE_CHECKING:
    from app.config import Settings


class AnnotationsRepository:
    """Stores per-connection schema annotations as JSON files."""

    def __init__(self, settings: "Settings"):
        self._store_dir = Path(".datachat_annotations")
        self._store_dir.mkdir(exist_ok=True)

    def _path(self, conn_id: str) -> Path:
        return self._store_dir / f"{conn_id}.json"

    async def save(self, annotations: SchemaAnnotations) -> SchemaAnnotations:
        self._path(annotations.conn_id).write_text(annotations.model_dump_json())
        return annotations

    async def get(self, conn_id: str) -> SchemaAnnotations | None:
        path = self._path(conn_id)
        if not path.exists():
            return None
        return SchemaAnnotations.model_validate_json(path.read_text())
