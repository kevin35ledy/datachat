from __future__ import annotations
import uuid
from datetime import datetime
from typing import Literal, TYPE_CHECKING
from pydantic import BaseModel, Field


class WidgetType(str):
    chart = "chart"
    table = "table"
    kpi = "kpi"
    text = "text"


WIDGET_TYPES = Literal["chart", "table", "kpi", "text"]
CHART_TYPES = Literal["bar", "line", "scatter", "pie", "bar_grouped", "area"]


class WidgetConfig(BaseModel):
    chart_type: CHART_TYPES | None = None
    x_column: str | None = None
    y_columns: list[str] = Field(default_factory=list)
    color: str | None = None
    title: str = ""


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


class WidgetRefreshResult(BaseModel):
    widget_id: str
    result: dict | None = None   # QueryResult serialized
    error: str | None = None


class DashboardRefreshResult(BaseModel):
    dashboard_id: str
    results: list[WidgetRefreshResult]
