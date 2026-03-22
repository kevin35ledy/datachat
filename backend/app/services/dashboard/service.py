from __future__ import annotations
import asyncio
from typing import TYPE_CHECKING
from app.core.models.dashboard import (
    Dashboard, DashboardWidget, WidgetConfig, WIDGET_TYPES,
)
from app.core.models.query import NLQuery, ChatResponse, QueryResult
from app.core.exceptions import DashboardWidgetCreationError
from app.services.nl2sql.service import NL2SQLService
from app.services.schema.service import SchemaService

if TYPE_CHECKING:
    from app.config import Settings
    from app.core.interfaces.connector import AbstractDatabaseConnector
    from app.core.interfaces.llm_provider import AbstractLLMProvider


class DashboardService:

    def __init__(self, settings: "Settings", llm: "AbstractLLMProvider"):
        self._settings = settings
        self._nl2sql = NL2SQLService(settings=settings, llm=llm)
        self._schema_service = SchemaService(settings)

    async def create_widget_from_nl(
        self,
        nl_text: str,
        widget_type_hint: WIDGET_TYPES,
        dashboard: Dashboard,
        connector: "AbstractDatabaseConnector",
    ) -> DashboardWidget:
        schema_info = await self._schema_service.get_schema(connector, dashboard.connection_id)

        nl_query = NLQuery(
            text=nl_text,
            session_id=f"dashboard-{dashboard.id}",
            connection_id=dashboard.connection_id,
        )

        response: ChatResponse = await self._nl2sql.generate_and_run(
            nl_query=nl_query,
            connector=connector,
            schema_info=schema_info,
            history=[],
        )

        if response.error or not response.sql_query or not response.result:
            raise DashboardWidgetCreationError(
                response.error or "Le pipeline NL2SQL n'a retourné aucun résultat."
            )

        resolved_type = _infer_widget_type(widget_type_hint, response)
        config = _build_config_from_suggestion(response.chart_suggestion, resolved_type)
        position = max((w.position for w in dashboard.widgets), default=-1) + 1
        title = (response.summary or nl_text)[:80].strip()

        return DashboardWidget(
            widget_type=resolved_type,
            title=title,
            nl_query=nl_text,
            sql_query=response.sql_query.validated_sql,
            config=config,
            position=position,
        )

    async def execute_widget(
        self,
        widget: DashboardWidget,
        connector: "AbstractDatabaseConnector",
    ) -> QueryResult:
        from app.services.nl2sql.sql_executor import SQLExecutor
        executor = SQLExecutor(self._settings)
        return await executor.execute(widget.sql_query, connector)

    async def execute_all_widgets(
        self,
        dashboard: Dashboard,
        connector: "AbstractDatabaseConnector",
    ) -> dict[str, QueryResult | str]:
        results = await asyncio.gather(
            *[self.execute_widget(w, connector) for w in dashboard.widgets],
            return_exceptions=True,
        )
        return {
            w.id: (r if not isinstance(r, Exception) else str(r))
            for w, r in zip(dashboard.widgets, results)
        }


# --- Helpers ---

def _infer_widget_type(hint: WIDGET_TYPES, response: ChatResponse) -> WIDGET_TYPES:
    """Upgrade chart → kpi when result is a single numeric value."""
    if hint != "chart":
        return hint
    result = response.result
    if result and result.total_count == 1 and len(result.columns) == 1:
        col = result.columns[0]
        if col.type_category == "numeric":
            return "kpi"
    return hint


def _build_config_from_suggestion(suggestion, widget_type: WIDGET_TYPES) -> WidgetConfig:
    if suggestion is None or widget_type not in ("chart",):
        return WidgetConfig()
    return WidgetConfig(
        chart_type=suggestion.type,
        x_column=suggestion.x_column,
        y_columns=suggestion.y_columns or ([suggestion.y_column] if suggestion.y_column else []),
    )
