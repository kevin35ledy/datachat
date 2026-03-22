from __future__ import annotations
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, SecretStr


DBType = Literal["postgresql", "mysql", "sqlite", "csv", "mongodb", "bigquery"]


class ConnectionConfig(BaseModel):
    """Stored configuration for a database connection."""

    id: str
    name: str
    db_type: DBType
    url: str  # Connection string (may contain credentials — encrypt at rest)
    database: str = ""
    schema_name: str = "public"
    ssl: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Not persisted — only used during connection test/use
    password: SecretStr | None = None


class ConnectionStatus(BaseModel):
    """Result of a connection test."""

    conn_id: str
    healthy: bool
    latency_ms: int | None = None
    error: str | None = None
    checked_at: datetime = Field(default_factory=datetime.utcnow)


class ConnectionCreate(BaseModel):
    """Input model for creating a new connection."""

    name: str
    db_type: DBType
    url: str
    schema_name: str = "public"
    ssl: bool = False
