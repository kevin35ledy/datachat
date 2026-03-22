from __future__ import annotations
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from app.config import Settings, get_settings
from app.core.models.query import NLQuery, ChatResponse
from app.repositories.connection_repo import ConnectionRepository
from app.repositories.query_repo import QueryRepository
from app.connectors.registry import ConnectorRegistry
from app.llm.registry import LLMRegistry
from app.services.nl2sql.service import NL2SQLService
from app.services.schema.service import SchemaService
from pydantic import BaseModel

router = APIRouter()


class ChatRequest(BaseModel):
    text: str
    connection_id: str
    session_id: str = "default"


def get_deps(settings: Annotated[Settings, Depends(get_settings)]):
    return settings


@router.post("/", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ChatResponse:
    conn_repo = ConnectionRepository(settings)
    registry = ConnectorRegistry(settings)
    llm_registry = LLMRegistry(settings)
    schema_service = SchemaService(settings)

    # Load connection config
    config = await conn_repo.get(body.connection_id)
    if config is None:
        raise HTTPException(status_code=404, detail=f"Connection '{body.connection_id}' not found")

    # Get or create connector
    connector = await registry.connect(config)

    # Get schema (cached)
    try:
        schema_info = await schema_service.get_schema(connector, body.connection_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Schema introspection failed: {e}")

    # Get LLM provider
    llm = llm_registry.get_default()

    # Build NL2SQL service and run
    service = NL2SQLService(settings=settings, llm=llm)
    nl_query = NLQuery(
        text=body.text,
        session_id=body.session_id,
        connection_id=body.connection_id,
    )

    response = await service.generate_and_run(
        nl_query=nl_query,
        connector=connector,
        schema_info=schema_info,
        history=[],
    )

    # Persist to history
    if response.sql_query and response.result:
        query_repo = QueryRepository(settings)
        await query_repo.save(
            connection_id=body.connection_id,
            session_id=body.session_id,
            nl_text=body.text,
            sql_text=response.sql_query.validated_sql,
            row_count=response.result.total_count,
            execution_time_ms=response.result.execution_time_ms,
        )

    return response


@router.get("/history")
async def get_history(
    connection_id: str,
    settings: Annotated[Settings, Depends(get_settings)],
    limit: int = 50,
):
    repo = QueryRepository(settings)
    return await repo.list_by_connection(connection_id, limit=limit)
