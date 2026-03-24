from __future__ import annotations
import uuid
from datetime import datetime
from typing import Literal, TYPE_CHECKING
from pydantic import BaseModel, Field, model_validator


class WidgetType(str):
    chart = "chart"
    table = "table"
    kpi = "kpi"
    text = "text"


WIDGET_TYPES = Literal["chart", "table", "kpi", "text", "pivot"]
CHART_TYPES = Literal["bar", "line", "scatter", "pie", "bar_grouped", "area"]


class PivotAggregation(BaseModel):
    field: str
    agg: str = "sum"   # sum|count|avg|min|max
    label: str = ""    # custom label; empty = auto-generated on frontend


class WidgetConfig(BaseModel):
    chart_type: CHART_TYPES | None = None
    x_column: str | None = None
    y_columns: list[str] = Field(default_factory=list)
    color: str | None = None
    title: str = ""
    inferred: bool = False  # True when config was built from heuristics, not from a clear chart suggestion
    # Pivot (TCD) config
    pivot_row_cols: list[str] = Field(default_factory=list)
    pivot_col_cols: list[str] = Field(default_factory=list)
    pivot_aggregations: list[PivotAggregation] = Field(default_factory=list)
    # Deprecated — kept for backward-compat migration only
    pivot_value_cols: list[str] = Field(default_factory=list)
    pivot_agg: str = "sum"

    @model_validator(mode='before')
    @classmethod
    def _migrate_pivot_fields(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        # v1 singular → v2 plural arrays
        for old, new in [
            ('pivot_row_col',   'pivot_row_cols'),
            ('pivot_col_col',   'pivot_col_cols'),
            ('pivot_value_col', 'pivot_value_cols'),
        ]:
            if old in data and not data.get(new):
                val = data[old]
                if val:
                    data[new] = [val]
        # v2 pivot_value_cols → v3 pivot_aggregations
        if not data.get('pivot_aggregations') and data.get('pivot_value_cols'):
            agg_type = data.get('pivot_agg', 'sum')
            data['pivot_aggregations'] = [
                {'field': vc, 'agg': agg_type, 'label': ''}
                for vc in data['pivot_value_cols']
            ]
        return data


class DashboardWidget(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    widget_type: WIDGET_TYPES
    title: str
    nl_query: str
    sql_query: str
    config: WidgetConfig = Field(default_factory=WidgetConfig)
    position: int = 0
    width: Literal[1, 2, 3] = 3   # 1=4col, 2=6col, 3=12col (12-col grid)
    height: Literal[1, 2] = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Dashboard(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    connection_id: str
    widgets: list[DashboardWidget] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DashboardCreate(BaseModel):
    name: str
    description: str = ""
    connection_id: str


class DashboardUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    widgets: list[DashboardWidget] | None = None


class AddWidgetRequest(BaseModel):
    nl_text: str
    widget_type: WIDGET_TYPES = "chart"


class AddWidgetResponse(BaseModel):
    dashboard: "Dashboard"
    warnings: list[str] = Field(default_factory=list)


class WidgetRefreshResult(BaseModel):
    widget_id: str
    result: dict | None = None   # QueryResult serialized
    error: str | None = None


class DashboardRefreshResult(BaseModel):
    dashboard_id: str
    results: list[WidgetRefreshResult]
