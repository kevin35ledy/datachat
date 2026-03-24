from __future__ import annotations
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class ColumnAnnotation(BaseModel):
    description: str = ""
    possible_values: list[str] = Field(default_factory=list)


class TableAnnotation(BaseModel):
    description: str = ""
    columns: dict[str, ColumnAnnotation] = Field(default_factory=dict)


class SchemaAnnotations(BaseModel):
    conn_id: str
    tables: dict[str, TableAnnotation] = Field(default_factory=dict)
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
