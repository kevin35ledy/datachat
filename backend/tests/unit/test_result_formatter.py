import pytest
from app.services.nl2sql.result_formatter import ResultFormatter
from app.core.models.query import QueryResult, ColumnMeta


@pytest.fixture
def formatter():
    return ResultFormatter()


def make_result(columns: list[tuple[str, str]], rows: list[dict]) -> QueryResult:
    cols = [ColumnMeta(name=name, type_name=type_name) for name, type_name in columns]
    return QueryResult(columns=cols, rows=rows, total_count=len(rows), execution_time_ms=10)


class TestChartInference:
    def test_text_numeric_suggests_bar(self, formatter):
        result = make_result([("ville", "TEXT"), ("nb_clients", "INTEGER")], [{"ville": "Paris", "nb_clients": 10}] * 5)
        chart = formatter.infer_chart(result)
        assert chart is not None
        assert chart.type == "bar"
        assert chart.x_column == "ville"
        assert chart.y_column == "nb_clients"

    def test_date_numeric_suggests_line(self, formatter):
        result = make_result([("date", "DATE"), ("ca", "DECIMAL")], [{"date": "2024-01-01", "ca": 100}] * 5)
        chart = formatter.infer_chart(result)
        assert chart is not None
        assert chart.type == "line"

    def test_two_numerics_suggests_scatter(self, formatter):
        result = make_result([("x", "FLOAT"), ("y", "FLOAT")], [{"x": 1.0, "y": 2.0}] * 5)
        chart = formatter.infer_chart(result)
        assert chart is not None
        assert chart.type == "scatter"

    def test_single_row_no_chart(self, formatter):
        result = make_result([("count", "INTEGER")], [{"count": 42}])
        chart = formatter.infer_chart(result)
        assert chart is None

    def test_empty_result_no_chart(self, formatter):
        result = make_result([("ville", "TEXT"), ("nb", "INTEGER")], [])
        chart = formatter.infer_chart(result)
        assert chart is None


class TestRowSerialization:
    def test_serializes_dates(self, formatter):
        import datetime
        result = make_result([("dt", "DATE")], [{"dt": datetime.date(2024, 1, 15)}])
        formatted = formatter.format(result)
        assert formatted.rows[0]["dt"] == "2024-01-15"

    def test_serializes_decimals(self, formatter):
        from decimal import Decimal
        result = make_result([("amount", "DECIMAL")], [{"amount": Decimal("123.45")}])
        formatted = formatter.format(result)
        assert formatted.rows[0]["amount"] == pytest.approx(123.45)

    def test_passes_through_strings(self, formatter):
        result = make_result([("name", "TEXT")], [{"name": "Alice"}])
        formatted = formatter.format(result)
        assert formatted.rows[0]["name"] == "Alice"
