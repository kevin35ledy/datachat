from __future__ import annotations
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from app.config import Settings, get_settings
from app.core.models.schema import SchemaInfo
from app.repositories.connection_repo import ConnectionRepository
from app.connectors.registry import ConnectorRegistry
from app.services.schema.service import SchemaService

router = APIRouter()


@router.get("/{conn_id}", response_model=SchemaInfo)
async def get_schema(
    conn_id: str,
    settings: Annotated[Settings, Depends(get_settings)],
    refresh: bool = False,
) -> SchemaInfo:
    conn_repo = ConnectionRepository(settings)
    registry = ConnectorRegistry(settings)
    schema_service = SchemaService(settings)

    config = await conn_repo.get(conn_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Connection not found")

    connector = await registry.connect(config)

    if refresh:
        schema_service.invalidate(conn_id)

    return await schema_service.get_schema(connector, conn_id)
