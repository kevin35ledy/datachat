import pytest
from app.config import Settings


@pytest.fixture
def settings() -> Settings:
    """Test settings with safe defaults."""
    return Settings(
        anthropic_api_key="test-key",
        secret_key="test-secret-key-for-unit-tests-only",
        litellm_default_model="claude-haiku-4-5-20251001",
        max_query_rows=100,
        query_timeout_seconds=5,
        debug=True,
    )


@pytest.fixture
def sample_schema():
    """A simple schema for testing."""
    from app.core.models.schema import SchemaInfo, TableInfo, ColumnInfo, ForeignKey
    return SchemaInfo(
        database_name="test_db",
        dialect="sqlite",
        tables=[
            TableInfo(
                name="clients",
                schema_name="main",
                columns=[
                    ColumnInfo(name="id", type_name="INTEGER", nullable=False, is_primary_key=True),
                    ColumnInfo(name="nom", type_name="TEXT", nullable=False),
                    ColumnInfo(name="email", type_name="TEXT", nullable=True),
                    ColumnInfo(name="ville", type_name="TEXT", nullable=True),
                ],
                row_count=100,
            ),
            TableInfo(
                name="commandes",
                schema_name="main",
                columns=[
                    ColumnInfo(name="id", type_name="INTEGER", nullable=False, is_primary_key=True),
                    ColumnInfo(name="client_id", type_name="INTEGER", nullable=False, is_foreign_key=True),
                    ColumnInfo(name="montant", type_name="REAL", nullable=True),
                    ColumnInfo(name="date_commande", type_name="DATE", nullable=True),
                ],
                foreign_keys=[
                    ForeignKey(column="client_id", ref_table="clients", ref_column="id"),
                ],
                row_count=500,
            ),
        ],
    )
