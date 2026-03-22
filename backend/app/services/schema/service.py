from __future__ import annotations
from typing import TYPE_CHECKING
import structlog
from app.core.models.schema import SchemaInfo

if TYPE_CHECKING:
    from app.config import Settings
    from app.core.interfaces.connector import AbstractDatabaseConnector

logger = structlog.get_logger()


class SchemaService:
    """
    Manages schema introspection and caching.

    In Phase 1, schema is cached in memory per connection.
    Phase 3 will add Qdrant-based embedding for schema RAG on large databases.
    """

    _cache: dict[str, SchemaInfo] = {}

    def __init__(self, settings: "Settings"):
        self._settings = settings

    async def get_schema(
        self,
        connector: "AbstractDatabaseConnector",
        conn_id: str,
    ) -> SchemaInfo:
        """Return schema, using cache when available."""
        if conn_id in self.__class__._cache:
            return self.__class__._cache[conn_id]

        logger.info("schema_introspecting", conn_id=conn_id)
        schema = await connector.introspect_schema()
        self.__class__._cache[conn_id] = schema
        logger.info("schema_loaded", conn_id=conn_id, tables=len(schema.tables))
        return schema

    def invalidate(self, conn_id: str) -> None:
        """Remove cached schema for a connection (force refresh on next call)."""
        self.__class__._cache.pop(conn_id, None)

    def invalidate_all(self) -> None:
        self.__class__._cache.clear()
