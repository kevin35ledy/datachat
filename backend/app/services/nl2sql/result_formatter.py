from __future__ import annotations
import re
from typing import TYPE_CHECKING
from app.core.models.query import QueryResult, ChartSuggestion, ColumnMeta

if TYPE_CHECKING:
    pass


_KEYWORD_MAP: list[tuple[list[str], str]] = [
    (["camembert", "tarte", "répartition", "proportion", "part de", "distribution", "pie"], "pie"),
    (["évolution", "tendance", "progression", "chronologique", "temporel", "historique", "line", "courbe"], "line"),
    (["aire", "area", "cumulé", "cumulatif"], "area"),
    (["corrélation", "nuage", "scatter", "dispersion"], "scatter"),
]


def _keyword_chart_type(nl_text: str) -> str | None:
    """Return a chart type if the NL query contains semantic keywords."""
    if not nl_text:
        return None
    text = nl_text.lower()
    for keywords, chart_type in _KEYWORD_MAP:
        if any(kw in text for kw in keywords):
            return chart_type
    return None


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


def _infer_category_from_values(col_name: str, rows: list[dict]) -> str:
    """Fallback: inspect actual row values when type_name gives no information."""
    for row in rows[:5]:
        val = row.get(col_name)
        if val is None:
            continue
        if isinstance(val, bool):
            return "boolean"
        if isinstance(val, (int, float)):
            return "numeric"
        import datetime
        if isinstance(val, (datetime.date, datetime.datetime)):
            return "date"
        return "text"
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
        # Serialize first so value-based inference sees Python types, not raw DB objects
        result.rows = [self._serialize_row(row) for row in result.rows]

        for col in result.columns:
            if col.type_category in ("unknown", "text"):
                by_name = _classify_column_category(col)
                if by_name != "text":
                    col.type_category = by_name
                elif col.type_name.lower() in ("unknown", ""):
                    # type_name gives nothing — fall back to actual values
                    col.type_category = _infer_category_from_values(col.name, result.rows)
                    col.inferred = True
                else:
                    col.type_category = by_name

        return result

    def infer_chart(self, result: QueryResult, nl_text: str = "") -> ChartSuggestion | None:
        """Suggest the most appropriate chart type for the result shape.

        nl_text is used for semantic keyword detection (higher priority than shape rules).
        """
        if result.total_count < 2 or not result.columns:
            return None

        cols = result.columns
        # Prefer already-enriched type_category; fall back to type_name classification
        categories = [
            c.type_category if c.type_category not in ("unknown",)
            else _classify_column_category(c)
            for c in cols
        ]

        text_names = [cols[i].name for i, c in enumerate(categories) if c == "text"]
        num_names = [cols[i].name for i, c in enumerate(categories) if c == "numeric"]
        date_names = [cols[i].name for i, c in enumerate(categories) if c == "date"]

        # --- Semantic keyword override (highest priority) ---
        keyword_type = _keyword_chart_type(nl_text)
        if keyword_type:
            x = text_names[0] if text_names else (date_names[0] if date_names else cols[0].name)
            y = num_names[0] if num_names else cols[-1].name
            if keyword_type == "scatter" and num_names:
                return ChartSuggestion(type="scatter", x_column=num_names[0], y_column=num_names[-1], y_columns=num_names)
            return ChartSuggestion(type=keyword_type, x_column=x, y_column=y, y_columns=num_names or [y])

        # --- Shape-based rules ---

        # Single text + single numeric → bar chart
        if len(cols) == 2 and categories[0] == "text" and categories[1] == "numeric":
            return ChartSuggestion(type="bar", x_column=cols[0].name, y_column=cols[1].name, y_columns=[cols[1].name])

        # Date/time + numeric → line chart
        if len(cols) >= 2 and categories[0] == "date" and categories[1] == "numeric":
            return ChartSuggestion(type="line", x_column=cols[0].name, y_column=cols[1].name, y_columns=[c.name for c in cols[1:] if categories[cols.index(c)] == "numeric"])

        # Two numerics → scatter
        if len(cols) == 2 and all(c == "numeric" for c in categories):
            return ChartSuggestion(type="scatter", x_column=cols[0].name, y_column=cols[1].name, y_columns=[cols[1].name])

        # Text + multiple numerics → grouped bar
        if len(cols) >= 3 and categories[0] == "text" and all(c == "numeric" for c in categories[1:]):
            return ChartSuggestion(
                type="bar_grouped",
                x_column=cols[0].name,
                y_column=cols[1].name,
                y_columns=[c.name for c in cols[1:]],
            )

        # Last resort: any text + any numeric column, regardless of position
        if text_names and num_names:
            return ChartSuggestion(
                type="bar",
                x_column=text_names[0],
                y_column=num_names[0],
                y_columns=num_names,
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
