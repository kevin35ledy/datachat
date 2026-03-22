from __future__ import annotations
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from app.config import Settings, get_settings
from app.core.models.connection import ConnectionConfig, ConnectionCreate, ConnectionStatus
from app.repositories.connection_repo import ConnectionRepository
from app.connectors.registry import ConnectorRegistry
import uuid

router = APIRouter()


def get_connection_repo(settings: Annotated[Settings, Depends(get_settings)]) -> ConnectionRepository:
    return ConnectionRepository(settings)


def get_registry(settings: Annotated[Settings, Depends(get_settings)]) -> ConnectorRegistry:
    return ConnectorRegistry(settings)


@router.get("/", response_model=list[ConnectionConfig])
async def list_connections(
    repo: Annotated[ConnectionRepository, Depends(get_connection_repo)],
) -> list[ConnectionConfig]:
    return await repo.list_all()


@router.post("/", response_model=ConnectionConfig, status_code=status.HTTP_201_CREATED)
async def create_connection(
    data: ConnectionCreate,
    repo: Annotated[ConnectionRepository, Depends(get_connection_repo)],
) -> ConnectionConfig:
    config = ConnectionConfig(
        id=str(uuid.uuid4()),
        name=data.name,
        db_type=data.db_type,
        url=data.url,
        schema_name=data.schema_name,
        ssl=data.ssl,
    )
    return await repo.save(config)


@router.post("/{conn_id}/test", response_model=ConnectionStatus)
async def test_connection(
    conn_id: str,
    repo: Annotated[ConnectionRepository, Depends(get_connection_repo)],
    registry: Annotated[ConnectorRegistry, Depends(get_registry)],
) -> ConnectionStatus:
    import time
    config = await repo.get(conn_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Connection not found")

    start = time.monotonic()
    try:
        connector = registry._build_connector(config)
        await connector.connect()
        healthy = await connector.test_connection()
        await connector.disconnect()
        elapsed = int((time.monotonic() - start) * 1000)
    except Exception as e:
        return ConnectionStatus(conn_id=conn_id, healthy=False, error=str(e))

    return ConnectionStatus(conn_id=conn_id, healthy=healthy, latency_ms=elapsed)


@router.delete("/{conn_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    conn_id: str,
    repo: Annotated[ConnectionRepository, Depends(get_connection_repo)],
    registry: Annotated[ConnectorRegistry, Depends(get_registry)],
) -> None:
    config = await repo.get(conn_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Connection not found")
    await registry.disconnect(conn_id)
    await repo.delete(conn_id)
