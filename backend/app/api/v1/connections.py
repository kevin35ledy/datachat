from __future__ import annotations
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from app.config import Settings, get_settings
from app.core.models.connection import ConnectionConfig, ConnectionCreate, ConnectionStatus
from app.core.models.annotations import SchemaAnnotations
from app.core.models.schema import SchemaInfo
from app.core.models.clarification import ClarificationRequest, ClarificationResponse
from app.repositories.connection_repo import ConnectionRepository
from app.repositories.annotations_repo import AnnotationsRepository
from app.connectors.registry import ConnectorRegistry
from app.services.schema.service import SchemaService
from app.llm.registry import LLMRegistry
import uuid

router = APIRouter()


def get_connection_repo(settings: Annotated[Settings, Depends(get_settings)]) -> ConnectionRepository:
    return ConnectionRepository(settings)


def get_registry(settings: Annotated[Settings, Depends(get_settings)]) -> ConnectorRegistry:
    return ConnectorRegistry(settings)


def get_annotations_repo(settings: Annotated[Settings, Depends(get_settings)]) -> AnnotationsRepository:
    return AnnotationsRepository(settings)


def get_schema_service(settings: Annotated[Settings, Depends(get_settings)]) -> SchemaService:
    return SchemaService(settings)


def get_llm_registry(settings: Annotated[Settings, Depends(get_settings)]) -> LLMRegistry:
    return LLMRegistry(settings)


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


@router.get("/{conn_id}/schema", response_model=SchemaInfo)
async def get_connection_schema(
    conn_id: str,
    repo: Annotated[ConnectionRepository, Depends(get_connection_repo)],
    registry: Annotated[ConnectorRegistry, Depends(get_registry)],
    annotations_repo: Annotated[AnnotationsRepository, Depends(get_annotations_repo)],
    schema_service: Annotated[SchemaService, Depends(get_schema_service)],
) -> SchemaInfo:
    config = await repo.get(conn_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Connection not found")
    connector = await registry.connect(config)
    return await schema_service.get_schema(connector, conn_id, annotations_repo)


@router.get("/{conn_id}/annotations", response_model=SchemaAnnotations)
async def get_annotations(
    conn_id: str,
    annotations_repo: Annotated[AnnotationsRepository, Depends(get_annotations_repo)],
) -> SchemaAnnotations:
    result = await annotations_repo.get(conn_id)
    if result is None:
        return SchemaAnnotations(conn_id=conn_id)
    return result


@router.put("/{conn_id}/annotations", response_model=SchemaAnnotations)
async def save_annotations(
    conn_id: str,
    data: SchemaAnnotations,
    annotations_repo: Annotated[AnnotationsRepository, Depends(get_annotations_repo)],
    schema_service: Annotated[SchemaService, Depends(get_schema_service)],
) -> SchemaAnnotations:
    data.conn_id = conn_id
    result = await annotations_repo.save(data)
    schema_service.invalidate(conn_id)
    return result


@router.post("/{conn_id}/clarify", response_model=ClarificationResponse)
async def clarify(
    conn_id: str,
    body: ClarificationRequest,
    repo: Annotated[ConnectionRepository, Depends(get_connection_repo)],
    registry: Annotated[ConnectorRegistry, Depends(get_registry)],
    annotations_repo: Annotated[AnnotationsRepository, Depends(get_annotations_repo)],
    schema_service: Annotated[SchemaService, Depends(get_schema_service)],
    llm_registry: Annotated[LLMRegistry, Depends(get_llm_registry)],
) -> ClarificationResponse:
    config = await repo.get(conn_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Connection not found")
    connector = await registry.connect(config)
    schema_info = await schema_service.get_schema(connector, conn_id, annotations_repo)

    from app.services.clarification.service import ClarificationService
    llm = llm_registry.get_default()
    svc = ClarificationService(settings=registry._settings, llm=llm)
    questions = await svc.get_questions(body.nl_text, schema_info)
    return ClarificationResponse(questions=questions)


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
