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
    from app.core.models.query import ChartSuggestion


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
    ) -> tuple[DashboardWidget, list[str]]:
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

        warnings: list[str] = []

        # Warn when column types were deduced from values (no DB metadata, e.g. SQLite)
        if any(c.inferred for c in response.result.columns):
            warnings.append(
                "Les types de colonnes ont été déduits des valeurs car la base de données "
                "ne fournit pas de métadonnées de type (ex: SQLite). "
                "La suggestion de graphique peut être inexacte."
            )

        resolved_type = _infer_widget_type(widget_type_hint, response)
        config = _build_config_from_suggestion(
            response.chart_suggestion, resolved_type, result=response.result
        )

        # Warn when no chart suggestion was available and we fell back to heuristics
        if resolved_type == "chart" and config.inferred:
            warnings.append(
                "Impossible de détecter automatiquement le meilleur type de graphique. "
                "Un graphique en barres a été généré par défaut — modifiez-le si nécessaire."
            )

        position = max((w.position for w in dashboard.widgets), default=-1) + 1
        title = (response.summary or nl_text)[:80].strip()

        widget = DashboardWidget(
            widget_type=resolved_type,
            title=title,
            nl_query=nl_text,
            sql_query=response.sql_query.validated_sql,
            config=config,
            position=position,
        )
        return widget, warnings

    async def regenerate_widget(
        self,
        nl_text: str,
        existing_widget: DashboardWidget,
        dashboard: Dashboard,
        connector: "AbstractDatabaseConnector",
    ) -> tuple[DashboardWidget, list[str]]:
        new_widget, warnings = await self.create_widget_from_nl(
            nl_text=nl_text,
            widget_type_hint=existing_widget.widget_type,
            dashboard=dashboard,
            connector=connector,
        )
        # Preserve identity and layout from the existing widget
        new_widget.id = existing_widget.id
        new_widget.position = existing_widget.position
        new_widget.width = existing_widget.width
        new_widget.height = existing_widget.height
        return new_widget, warnings

    async def execute_widget(
        self,
        widget: DashboardWidget,
        connector: "AbstractDatabaseConnector",
    ) -> QueryResult:
        from app.services.nl2sql.sql_executor import SQLExecutor
        from app.services.nl2sql.result_formatter import ResultFormatter
        executor = SQLExecutor(self._settings)
        result = await executor.execute(widget.sql_query, connector)
        return ResultFormatter().format(result)

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
    """Upgrade chart → kpi when result is a single numeric value. Preserve pivot/table/text."""
    if hint in ("pivot", "table", "text"):
        return hint
    if hint != "chart":
        return hint
    result = response.result
    if result and result.total_count == 1 and len(result.columns) == 1:
        col = result.columns[0]
        if col.type_category == "numeric":
            return "kpi"
    return hint


def _build_config_from_suggestion(
    suggestion: "ChartSuggestion | None",
    widget_type: WIDGET_TYPES,
    result: QueryResult | None = None,
) -> WidgetConfig:
    if suggestion is not None and widget_type in ("chart",):
        return WidgetConfig(
            chart_type=suggestion.type,
            x_column=suggestion.x_column,
            y_columns=suggestion.y_columns or ([suggestion.y_column] if suggestion.y_column else []),
        )
    if widget_type == "chart" and result is not None:
        return _config_from_result(result)
    return WidgetConfig()


def _config_from_result(result: QueryResult) -> WidgetConfig:
    """Last-resort: build a bar chart config from column shape and first-row values."""
    text_cols = [c.name for c in result.columns if c.type_category in ("text", "unknown")]
    num_cols = [c.name for c in result.columns if c.type_category == "numeric"]
    if not num_cols and result.rows:
        first = result.rows[0]
        num_cols = [k for k, v in first.items() if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if not text_cols:
            text_cols = [k for k, v in first.items() if isinstance(v, str)]
    if num_cols:
        x = text_cols[0] if text_cols else result.columns[0].name
        return WidgetConfig(chart_type="bar", x_column=x, y_columns=num_cols, inferred=True)
    return WidgetConfig(inferred=True)
