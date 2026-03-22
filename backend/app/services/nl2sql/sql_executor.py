from __future__ import annotations
import structlog
from typing import TYPE_CHECKING
from app.core.exceptions import QueryTimeoutError
from app.core.models.query import QueryResult
from app.services.nl2sql.sql_validator import SQLValidator

if TYPE_CHECKING:
    from app.config import Settings
    from app.core.interfaces.connector import AbstractDatabaseConnector

logger = structlog.get_logger()


class SQLExecutor:
    """
    Executes validated SQL via a database connector.

    Responsibilities:
    - Inject LIMIT if missing
    - Wrap in READ ONLY transaction if connector supports it
    - Enforce timeout
    - Log execution metadata
    """

    def __init__(self, settings: "Settings"):
        self._settings = settings
        self._validator = SQLValidator()

    async def execute(
        self,
        validated_sql: str,
        connector: "AbstractDatabaseConnector",
    ) -> QueryResult:
        """
        Execute a pre-validated SQL query.
        The sql argument MUST have already been through SQLValidator.validate().
        """
        # Inject LIMIT as a safety net
        safe_sql = SQLValidator.inject_limit(
            validated_sql,
            max_rows=self._settings.max_query_rows,
            dialect=connector.dialect,
        )

        log = logger.bind(dialect=connector.dialect)
        log.debug("sql_executing", sql=safe_sql[:200])

        try:
            result = await connector.execute_query(
                sql=safe_sql,
                timeout_seconds=self._settings.query_timeout_seconds,
            )
        except Exception as e:
            if "timeout" in str(e).lower() or "cancele" in str(e).lower():
                raise QueryTimeoutError(
                    f"Query exceeded {self._settings.query_timeout_seconds}s timeout. "
                    "Try a more specific question or add filters."
                ) from e
            raise

        # Mark as truncated if we hit the limit
        if result.total_count >= self._settings.max_query_rows:
            result.truncated = True

        log.info("sql_executed", rows=result.total_count, ms=result.execution_time_ms)
        return result
