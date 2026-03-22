from __future__ import annotations
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class AbstractDatabaseConnector(Protocol):
    """
    Protocol that every database connector must satisfy.

    Implementations live in app/connectors/. Register them in app/connectors/registry.py.
    See docs/guides/add-db-connector.md for the step-by-step guide.
    """

    async def connect(self) -> None:
        """Establish connection pool. Called once when the connection is first used."""
        ...

    async def disconnect(self) -> None:
        """Gracefully close all connections and release pool resources."""
        ...

    async def test_connection(self) -> bool:
        """Verify connectivity without side effects. Returns True if healthy."""
        ...

    async def execute_query(
        self,
        sql: str,
        parameters: dict[str, Any] | None = None,
        timeout_seconds: int = 30,
    ) -> "QueryResult":
        """
        Execute a validated SELECT query and return structured results.
        The sql argument has already been validated by SQLValidator.
        Never call this directly with user-supplied SQL.
        """
        ...

    async def introspect_schema(self) -> "SchemaInfo":
        """
        Return complete schema metadata: tables, columns, types, constraints, FK, indexes.
        This is used to build the schema RAG embeddings and for audit checks.
        """
        ...

    async def explain_query(self, sql: str) -> dict[str, Any]:
        """Return the native query execution plan (EXPLAIN output)."""
        ...

    async def get_table_sample(
        self, table: str, limit: int = 5
    ) -> "QueryResult":
        """Return sample rows for LLM prompt context (schema understanding)."""
        ...

    @property
    def dialect(self) -> str:
        """sqlglot dialect string: 'postgres', 'mysql', 'sqlite', 'duckdb', etc."""
        ...

    @property
    def supports_transactions(self) -> bool:
        """True if the connector supports READ ONLY transaction wrapping."""
        ...


# Forward references resolved at runtime — avoid circular imports
from app.core.models.query import QueryResult  # noqa: E402
from app.core.models.schema import SchemaInfo  # noqa: E402
