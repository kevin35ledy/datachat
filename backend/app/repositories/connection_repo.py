from __future__ import annotations
import json
from pathlib import Path
from typing import TYPE_CHECKING
from app.core.models.connection import ConnectionConfig
from app.utils.crypto import encrypt_url, decrypt_url

if TYPE_CHECKING:
    from app.config import Settings


class ConnectionRepository:
    """
    Stores connection configurations as encrypted JSON files.
    Phase 1: file-based storage. Phase 4: migrate to PostgreSQL.
    """

    def __init__(self, settings: "Settings"):
        self._settings = settings
        self._store_dir = Path(".dbia_connections")
        self._store_dir.mkdir(exist_ok=True)

    def _path(self, conn_id: str) -> Path:
        return self._store_dir / f"{conn_id}.json"

    async def save(self, config: ConnectionConfig) -> ConnectionConfig:
        data = config.model_dump()
        data["url"] = encrypt_url(config.url, self._settings.secret_key)
        self._path(config.id).write_text(json.dumps(data, default=str))
        return config

    async def get(self, conn_id: str) -> ConnectionConfig | None:
        path = self._path(conn_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        data["url"] = decrypt_url(data["url"], self._settings.secret_key)
        return ConnectionConfig(**data)

    async def list_all(self) -> list[ConnectionConfig]:
        configs = []
        for path in self._store_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                data["url"] = decrypt_url(data["url"], self._settings.secret_key)
                configs.append(ConnectionConfig(**data))
            except Exception:
                continue
        return sorted(configs, key=lambda c: c.created_at)

    async def delete(self, conn_id: str) -> bool:
        path = self._path(conn_id)
        if path.exists():
            path.unlink()
            return True
        return False
