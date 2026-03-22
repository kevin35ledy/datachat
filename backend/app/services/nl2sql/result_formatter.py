from __future__ import annotations
import re
from typing import TYPE_CHECKING
from app.core.models.query import QueryResult, ChartSuggestion, ColumnMeta

if TYPE_CHECKING:
    pass


def _classify_column_category(col: ColumnMeta) -> str:
    """Infer the type category of a column from its type name."""
    t = col.type_name.lower()
    if any(x in t for x in ("int", "float", "double", "decimal", "numeric", "real", "number", "bigint", "smallint")):
        return "numeric"
    if any(x in t for x in ("date", "time", "timestamp")):
        return "date"
    if "bool" in t:
        return "boolean"
    if "json" in t:
        return "json"
    return "text"


class ResultFormatter:
    """
    Transforms raw QueryResult into a presentation-ready format.

    Responsibilities:
    - Enrich column metadata with inferred type categories
    - Suggest the best chart type based on result shape
    - Serialize row values to JSON-safe types
    """

    def format(self, result: QueryResult) -> QueryResult:
        """Enrich result with inferred type categories on columns."""
        for col in result.columns:
            if col.type_category == "unknown":
                col.type_category = _classify_column_category(col)

        # Serialize non-JSON-safe types
        result.rows = [self._serialize_row(row) for row in result.rows]
        return result

    def infer_chart(self, result: QueryResult) -> ChartSuggestion | None:
        """Suggest the most appropriate chart type for the result shape."""
        if result.total_count < 2 or not result.columns:
            return None

        cols = result.columns
        categories = [_classify_column_category(c) for c in cols]

        # Single text + single numeric → bar chart
        if len(cols) == 2 and categories[0] == "text" and categories[1] == "numeric":
            return ChartSuggestion(type="bar", x_column=cols[0].name, y_column=cols[1].name)

        # Date/time + numeric → line chart
        if len(cols) >= 2 and categories[0] == "date" and categories[1] == "numeric":
            return ChartSuggestion(type="line", x_column=cols[0].name, y_column=cols[1].name)

        # Two numerics → scatter
        if len(cols) == 2 and all(c == "numeric" for c in categories):
            return ChartSuggestion(type="scatter", x_column=cols[0].name, y_column=cols[1].name)

        # Text + multiple numerics → grouped bar
        if len(cols) >= 3 and categories[0] == "text" and all(c == "numeric" for c in categories[1:]):
            return ChartSuggestion(
                type="bar_grouped",
                x_column=cols[0].name,
                y_column=cols[1].name,
                y_columns=[c.name for c in cols[1:]],
            )

        return None

    @staticmethod
    def _serialize_row(row: dict) -> dict:
        """Convert non-JSON-serializable values to strings."""
        import datetime, decimal
        result = {}
        for k, v in row.items():
            if isinstance(v, (datetime.date, datetime.datetime)):
                result[k] = v.isoformat()
            elif isinstance(v, decimal.Decimal):
                result[k] = float(v)
            elif isinstance(v, bytes):
                result[k] = v.hex()
            else:
                result[k] = v
        return result
