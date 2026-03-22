from __future__ import annotations
import uuid
import time
from typing import Any, TYPE_CHECKING
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from app.core.models.query import QueryResult, ColumnMeta

if TYPE_CHECKING:
    from app.config import Settings
    from app.core.models.connection import ConnectionConfig


def _infer_type_category(type_name: str) -> str:
    t = type_name.lower()
    if any(x in t for x in ("int", "float", "double", "decimal", "numeric", "real", "number")):
        return "numeric"
    if any(x in t for x in ("date", "time", "timestamp")):
        return "date"
    if any(x in t for x in ("bool",)):
        return "boolean"
    if any(x in t for x in ("json",)):
        return "json"
    return "text"


class BaseConnector:
    """
    Shared SQLAlchemy logic for all SQL-based connectors.
    Subclasses override introspect_schema() and explain_query() for DB-specific SQL.
    """

    def __init__(self, config: "ConnectionConfig", settings: "Settings"):
        self.config = config
        self.settings = settings
        self._engine: AsyncEngine | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        self._engine = create_async_engine(
            self._async_url(),
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            echo=self.settings.debug,
        )

    async def disconnect(self) -> None:
        if self._engine:
            await self._engine.dispose()
            self._engine = None

    async def test_connection(self) -> bool:
        try:
            async with self._engine.connect() as conn:
                await conn.execute(sa_text("SELECT 1"))
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Query execution
    # ------------------------------------------------------------------

    async def execute_query(
        self,
        sql: str,
        parameters: dict[str, Any] | None = None,
        timeout_seconds: int = 30,
    ) -> QueryResult:
        start = time.monotonic()
        async with self._engine.connect() as conn:
            result = await conn.execute(sa_text(sql), parameters or {})
            rows_raw = result.fetchall()
            col_names = list(result.keys())
        elapsed_ms = int((time.monotonic() - start) * 1000)

        columns = [
            ColumnMeta(
                name=name,
                type_name="unknown",
                type_category="unknown",
            )
            for name in col_names
        ]
        rows = [dict(zip(col_names, row)) for row in rows_raw]

        return QueryResult(
            query_id=str(uuid.uuid4()),
            columns=columns,
            rows=rows,
            total_count=len(rows),
            truncated=False,
            execution_time_ms=elapsed_ms,
        )

    async def get_table_sample(self, table: str, limit: int = 5) -> QueryResult:
        return await self.execute_query(f"SELECT * FROM {table} LIMIT {limit}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _async_url(self) -> str:
        """Return the async-compatible SQLAlchemy URL."""
        return self.config.url

    def _generate_query_id(self) -> str:
        return str(uuid.uuid4())

    @property
    def supports_transactions(self) -> bool:
        return True
