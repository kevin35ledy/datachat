from __future__ import annotations
import uuid
from datetime import datetime
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from app.config import Settings, get_settings
from app.core.models.dashboard import (
    Dashboard, DashboardCreate, DashboardUpdate, AddWidgetRequest, AddWidgetResponse,
    DashboardRefreshResult, WidgetRefreshResult,
)
from app.core.exceptions import DashboardNotFoundError, DashboardWidgetCreationError
from app.repositories.dashboard_repo import DashboardRepository
from app.repositories.connection_repo import ConnectionRepository
from app.connectors.registry import ConnectorRegistry
from app.llm.registry import LLMRegistry
from app.services.dashboard.service import DashboardService

router = APIRouter()


def get_dashboard_repo(settings: Annotated[Settings, Depends(get_settings)]) -> DashboardRepository:
    return DashboardRepository(settings)


def get_connection_repo(settings: Annotated[Settings, Depends(get_settings)]) -> ConnectionRepository:
    return ConnectionRepository(settings)


def get_registry(settings: Annotated[Settings, Depends(get_settings)]) -> ConnectorRegistry:
    return ConnectorRegistry(settings)


def get_llm_registry(settings: Annotated[Settings, Depends(get_settings)]) -> LLMRegistry:
    return LLMRegistry(settings)


@router.get("/", response_model=list[Dashboard])
async def list_dashboards(
    repo: Annotated[DashboardRepository, Depends(get_dashboard_repo)],
) -> list[Dashboard]:
    return await repo.list_all()


@router.post("/", response_model=Dashboard, status_code=status.HTTP_201_CREATED)
async def create_dashboard(
    data: DashboardCreate,
    repo: Annotated[DashboardRepository, Depends(get_dashboard_repo)],
) -> Dashboard:
    now = datetime.utcnow()
    dashboard = Dashboard(
        id=str(uuid.uuid4()),
        name=data.name,
        description=data.description,
        connection_id=data.connection_id,
        created_at=now,
        updated_at=now,
    )
    return await repo.save(dashboard)


@router.get("/{dashboard_id}", response_model=Dashboard)
async def get_dashboard(
    dashboard_id: str,
    repo: Annotated[DashboardRepository, Depends(get_dashboard_repo)],
) -> Dashboard:
    dashboard = await repo.get(dashboard_id)
    if dashboard is None:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return dashboard


@router.put("/{dashboard_id}", response_model=Dashboard)
async def update_dashboard(
    dashboard_id: str,
    data: DashboardUpdate,
    repo: Annotated[DashboardRepository, Depends(get_dashboard_repo)],
) -> Dashboard:
    dashboard = await repo.get(dashboard_id)
    if dashboard is None:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    if data.name is not None:
        dashboard.name = data.name
    if data.description is not None:
        dashboard.description = data.description
    if data.widgets is not None:
        dashboard.widgets = data.widgets
    return await repo.save(dashboard)


@router.delete("/{dashboard_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dashboard(
    dashboard_id: str,
    repo: Annotated[DashboardRepository, Depends(get_dashboard_repo)],
) -> None:
    found = await repo.delete(dashboard_id)
    if not found:
        raise HTTPException(status_code=404, detail="Dashboard not found")


@router.post("/{dashboard_id}/widgets/from-nl", response_model=AddWidgetResponse)
async def add_widget_from_nl(
    dashboard_id: str,
    body: AddWidgetRequest,
    repo: Annotated[DashboardRepository, Depends(get_dashboard_repo)],
    conn_repo: Annotated[ConnectionRepository, Depends(get_connection_repo)],
    registry: Annotated[ConnectorRegistry, Depends(get_registry)],
    llm_registry: Annotated[LLMRegistry, Depends(get_llm_registry)],
) -> AddWidgetResponse:
    dashboard = await repo.get(dashboard_id)
    if dashboard is None:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    config = await conn_repo.get(dashboard.connection_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Connection not found")

    connector = await registry.connect(config)
    llm = llm_registry.get_default()
    service = DashboardService(settings=registry._settings, llm=llm)

    try:
        widget, warnings = await service.create_widget_from_nl(
            nl_text=body.nl_text,
            widget_type_hint=body.widget_type,
            dashboard=dashboard,
            connector=connector,
        )
    except DashboardWidgetCreationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    dashboard.widgets.append(widget)
    saved = await repo.save(dashboard)
    return AddWidgetResponse(dashboard=saved, warnings=warnings)


@router.delete("/{dashboard_id}/widgets/{widget_id}", response_model=Dashboard)
async def remove_widget(
    dashboard_id: str,
    widget_id: str,
    repo: Annotated[DashboardRepository, Depends(get_dashboard_repo)],
) -> Dashboard:
    dashboard = await repo.get(dashboard_id)
    if dashboard is None:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    dashboard.widgets = [w for w in dashboard.widgets if w.id != widget_id]
    # Re-number positions
    for i, w in enumerate(sorted(dashboard.widgets, key=lambda x: x.position)):
        w.position = i
    return await repo.save(dashboard)


@router.patch("/{dashboard_id}/widgets/{widget_id}/config", response_model=Dashboard)
async def update_widget_config(
    dashboard_id: str,
    widget_id: str,
    config: WidgetConfig,
    repo: Annotated[DashboardRepository, Depends(get_dashboard_repo)],
) -> Dashboard:
    """Update widget config (chart type, axes, pivot dims) without re-running SQL."""
    dashboard = await repo.get(dashboard_id)
    if dashboard is None:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    widget = next((w for w in dashboard.widgets if w.id == widget_id), None)
    if widget is None:
        raise HTTPException(status_code=404, detail="Widget not found")
    widget.config = config
    return await repo.save(dashboard)


@router.post("/{dashboard_id}/widgets/{widget_id}/regenerate", response_model=AddWidgetResponse)
async def regenerate_widget(
    dashboard_id: str,
    widget_id: str,
    body: AddWidgetRequest,
    repo: Annotated[DashboardRepository, Depends(get_dashboard_repo)],
    conn_repo: Annotated[ConnectionRepository, Depends(get_connection_repo)],
    registry: Annotated[ConnectorRegistry, Depends(get_registry)],
    llm_registry: Annotated[LLMRegistry, Depends(get_llm_registry)],
) -> AddWidgetResponse:
    dashboard = await repo.get(dashboard_id)
    if dashboard is None:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    existing = next((w for w in dashboard.widgets if w.id == widget_id), None)
    if existing is None:
        raise HTTPException(status_code=404, detail="Widget not found")

    config = await conn_repo.get(dashboard.connection_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Connection not found")

    connector = await registry.connect(config)
    llm = llm_registry.get_default()
    service = DashboardService(settings=registry._settings, llm=llm)

    try:
        new_widget, warnings = await service.regenerate_widget(
            nl_text=body.nl_text,
            existing_widget=existing,
            dashboard=dashboard,
            connector=connector,
        )
    except DashboardWidgetCreationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    dashboard.widgets = [new_widget if w.id == widget_id else w for w in dashboard.widgets]
    saved = await repo.save(dashboard)
    return AddWidgetResponse(dashboard=saved, warnings=warnings)


@router.get("/{dashboard_id}/widgets/{widget_id}/debug")
async def debug_widget(
    dashboard_id: str,
    widget_id: str,
    repo: Annotated[DashboardRepository, Depends(get_dashboard_repo)],
    conn_repo: Annotated[ConnectionRepository, Depends(get_connection_repo)],
    registry: Annotated[ConnectorRegistry, Depends(get_registry)],
) -> dict:
    """Debug endpoint: shows each pipeline layer's output for a widget."""
    dashboard = await repo.get(dashboard_id)
    if dashboard is None:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    widget = next((w for w in dashboard.widgets if w.id == widget_id), None)
    if widget is None:
        raise HTTPException(status_code=404, detail="Widget not found")

    config = await conn_repo.get(dashboard.connection_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Connection not found")

    connector = await registry.connect(config)

    from app.services.nl2sql.sql_executor import SQLExecutor
    from app.services.nl2sql.result_formatter import ResultFormatter

    executor = SQLExecutor(registry._settings)
    formatter = ResultFormatter()

    raw_result = await executor.execute(widget.sql_query, connector)
    raw_columns = [c.model_dump() for c in raw_result.columns]
    raw_first_row = raw_result.rows[0] if raw_result.rows else None

    formatted_result = formatter.format(raw_result)
    formatted_columns = [c.model_dump() for c in formatted_result.columns]
    chart_suggestion = formatter.infer_chart(formatted_result)

    return {
        "widget_id": widget_id,
        "widget_type": widget.widget_type,
        "sql": widget.sql_query,
        "stored_config": widget.config.model_dump(),
        "layer_1_raw_columns": raw_columns,
        "layer_1_first_row": raw_first_row,
        "layer_2_formatted_columns": formatted_columns,
        "layer_3_chart_suggestion": chart_suggestion.model_dump() if chart_suggestion else None,
        "row_count": formatted_result.total_count,
    }


@router.post("/{dashboard_id}/refresh", response_model=DashboardRefreshResult)
async def refresh_dashboard(
    dashboard_id: str,
    repo: Annotated[DashboardRepository, Depends(get_dashboard_repo)],
    conn_repo: Annotated[ConnectionRepository, Depends(get_connection_repo)],
    registry: Annotated[ConnectorRegistry, Depends(get_registry)],
    llm_registry: Annotated[LLMRegistry, Depends(get_llm_registry)],
) -> DashboardRefreshResult:
    dashboard = await repo.get(dashboard_id)
    if dashboard is None:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    if not dashboard.widgets:
        return DashboardRefreshResult(dashboard_id=dashboard_id, results=[])

    config = await conn_repo.get(dashboard.connection_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Connection not found")

    connector = await registry.connect(config)
    llm = llm_registry.get_default()
    service = DashboardService(settings=registry._settings, llm=llm)

    raw = await service.execute_all_widgets(dashboard, connector)

    results = []
    for widget_id, value in raw.items():
        if isinstance(value, str):
            results.append(WidgetRefreshResult(widget_id=widget_id, error=value))
        else:
            results.append(WidgetRefreshResult(
                widget_id=widget_id,
                result=value.model_dump(mode="json"),
            ))

    return DashboardRefreshResult(dashboard_id=dashboard_id, results=results)
