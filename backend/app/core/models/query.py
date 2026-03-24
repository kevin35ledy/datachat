from __future__ import annotations
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field
import uuid


class ColumnMeta(BaseModel):
    """Metadata for a single result column."""

    name: str
    type_name: str
    type_category: Literal["text", "numeric", "date", "boolean", "json", "unknown"] = "unknown"
    nullable: bool = True
    inferred: bool = False  # True when type_category was deduced from row values (no DB metadata)


class QueryResult(BaseModel):
    """Structured result of a database query execution."""

    query_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    columns: list[ColumnMeta]
    rows: list[dict[str, Any]]
    total_count: int
    truncated: bool = False  # True if row limit was applied
    execution_time_ms: int


class NLQuery(BaseModel):
    """An incoming natural language query from the user."""

    text: str
    session_id: str
    connection_id: str
    user_id: str | None = None


class SQLQuery(BaseModel):
    """A generated and validated SQL query."""

    raw_sql: str  # LLM output before validation
    validated_sql: str  # After sqlglot normalization — the ONLY sql passed to executor
    dialect: str
    is_safe: bool = True
    validation_warnings: list[str] = Field(default_factory=list)
    estimated_rows: int | None = None
    explanation: str = ""  # LLM's plain-English explanation of the query
    confidence: float = 1.0  # 0-1, from LLM response


class ChatResponse(BaseModel):
    """Complete response to a user's NL query."""

    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    nl_query: str
    sql_query: SQLQuery | None = None
    result: QueryResult | None = None
    chart_suggestion: "ChartSuggestion | None" = None
    summary: str = ""  # NL summary of the result
    error: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ChartSuggestion(BaseModel):
    """Suggested chart type and axis mapping for the result."""

    type: Literal["bar", "line", "scatter", "pie", "bar_grouped", "area"]
    x_column: str
    y_column: str
    y_columns: list[str] = Field(default_factory=list)  # For grouped charts


class QueryHistoryEntry(BaseModel):
    """A saved query from history."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    connection_id: str
    session_id: str
    nl_text: str
    sql_text: str
    row_count: int
    execution_time_ms: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
