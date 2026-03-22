from __future__ import annotations
from typing import Annotated
from fastapi import Depends, HTTPException, status
from app.config import Settings, get_settings
from app.connectors.registry import ConnectorRegistry
from app.llm.registry import LLMRegistry
from app.core.interfaces.connector import AbstractDatabaseConnector
from app.core.interfaces.llm_provider import AbstractLLMProvider


def get_connector_registry(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ConnectorRegistry:
    return ConnectorRegistry(settings)


def get_llm_registry(
    settings: Annotated[Settings, Depends(get_settings)],
) -> LLMRegistry:
    return LLMRegistry(settings)


async def get_connector(
    conn_id: str,
    registry: Annotated[ConnectorRegistry, Depends(get_connector_registry)],
) -> AbstractDatabaseConnector:
    connector = await registry.get(conn_id)
    if connector is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connection '{conn_id}' not found",
        )
    return connector


def get_llm_provider(
    registry: Annotated[LLMRegistry, Depends(get_llm_registry)],
) -> AbstractLLMProvider:
    return registry.get_default()
