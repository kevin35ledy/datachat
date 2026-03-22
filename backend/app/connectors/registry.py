from __future__ import annotations
from typing import TYPE_CHECKING
from app.core.exceptions import UnsupportedDatabaseError, ConnectionNotFoundError

if TYPE_CHECKING:
    from app.config import Settings
    from app.core.interfaces.connector import AbstractDatabaseConnector
    from app.core.models.connection import ConnectionConfig


class ConnectorRegistry:
    """Maps connection configs to their connector implementations."""

    def __init__(self, settings: "Settings"):
        self._settings = settings
        self._active: dict[str, "AbstractDatabaseConnector"] = {}

    def _build_connector(self, config: "ConnectionConfig") -> "AbstractDatabaseConnector":
        from app.connectors.sqlite import SQLiteConnector
        from app.connectors.postgresql import PostgreSQLConnector

        scheme = config.url.split("://")[0].lower().split("+")[0]
        registry_map = {
            "sqlite": SQLiteConnector,
            "postgresql": PostgreSQLConnector,
            "postgres": PostgreSQLConnector,
        }
        cls = registry_map.get(scheme)
        if cls is None:
            raise UnsupportedDatabaseError(
                f"No connector registered for scheme '{scheme}'. "
                f"Supported: {list(registry_map.keys())}"
            )
        return cls(config, self._settings)

    async def get(self, conn_id: str) -> "AbstractDatabaseConnector | None":
        """Return an active (connected) connector by connection ID."""
        return self._active.get(conn_id)

    async def connect(self, config: "ConnectionConfig") -> "AbstractDatabaseConnector":
        """Create, connect, and cache a connector for the given config."""
        if config.id in self._active:
            return self._active[config.id]
        connector = self._build_connector(config)
        await connector.connect()
        self._active[config.id] = connector
        return connector

    async def disconnect(self, conn_id: str) -> None:
        """Disconnect and remove a connector."""
        connector = self._active.pop(conn_id, None)
        if connector:
            await connector.disconnect()

    async def disconnect_all(self) -> None:
        """Disconnect all active connectors (called on shutdown)."""
        for conn_id in list(self._active.keys()):
            await self.disconnect(conn_id)
