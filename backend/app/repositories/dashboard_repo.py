from __future__ import annotations
import json
from pathlib import Path
from typing import TYPE_CHECKING
from app.core.models.dashboard import Dashboard

if TYPE_CHECKING:
    from app.config import Settings


class DashboardRepository:
    """
    Stores dashboards as plain JSON files in .datachat_dashboards/.
    No encryption needed — dashboards contain no credentials.
    """

    def __init__(self, settings: "Settings"):
        self._store_dir = Path(".datachat_dashboards")
        self._store_dir.mkdir(exist_ok=True)

    def _path(self, dashboard_id: str) -> Path:
        return self._store_dir / f"{dashboard_id}.json"

    async def save(self, dashboard: Dashboard) -> Dashboard:
        from datetime import datetime
        dashboard.updated_at = datetime.utcnow()
        self._path(dashboard.id).write_text(dashboard.model_dump_json())
        return dashboard

    async def get(self, dashboard_id: str) -> Dashboard | None:
        path = self._path(dashboard_id)
        if not path.exists():
            return None
        return Dashboard.model_validate_json(path.read_text())

    async def list_all(self) -> list[Dashboard]:
        dashboards = []
        for path in self._store_dir.glob("*.json"):
            try:
                dashboards.append(Dashboard.model_validate_json(path.read_text()))
            except Exception:
                continue
        return sorted(dashboards, key=lambda d: d.created_at)

    async def delete(self, dashboard_id: str) -> bool:
        path = self._path(dashboard_id)
        if path.exists():
            path.unlink()
            return True
        return False
