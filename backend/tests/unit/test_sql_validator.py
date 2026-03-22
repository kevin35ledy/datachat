import pytest
from app.services.nl2sql.sql_validator import SQLValidator
from app.core.exceptions import SQLSecurityError, SQLValidationError, SQLExtractionError


@pytest.fixture
def validator():
    return SQLValidator()


class TestSQLExtraction:
    def test_extracts_sql_tags(self, validator):
        response = "<sql>SELECT * FROM users</sql>"
        assert validator.extract_sql(response) == "SELECT * FROM users"

    def test_extracts_markdown_block(self, validator):
        response = "Here is the SQL:\n```sql\nSELECT COUNT(*) FROM clients\n```"
        result = validator.extract_sql(response)
        assert "SELECT COUNT(*)" in result

    def test_extracts_raw_select(self, validator):
        response = "SELECT id, nom FROM clients WHERE ville = 'Paris'"
        result = validator.extract_sql(response)
        assert result.startswith("SELECT")

    def test_raises_when_no_sql(self, validator):
        with pytest.raises(SQLExtractionError):
            validator.extract_sql("Je ne peux pas répondre à cette question.")

    def test_trims_whitespace(self, validator):
        response = "<sql>\n  SELECT 1  \n</sql>"
        result = validator.extract_sql(response)
        assert result == "SELECT 1"


class TestSQLValidation:
    def test_valid_select_passes(self, validator):
        sql = "SELECT id, nom FROM clients WHERE ville = 'Paris'"
        result = validator.validate(sql, dialect="sqlite")
        assert "SELECT" in result.upper()

    def test_blocks_drop_table(self, validator):
        sql = "DROP TABLE clients"
        with pytest.raises(SQLSecurityError, match="not allowed"):
            validator.validate(sql, dialect="sqlite")

    def test_blocks_delete(self, validator):
        sql = "DELETE FROM clients WHERE id = 1"
        with pytest.raises(SQLSecurityError, match="not allowed"):
            validator.validate(sql, dialect="sqlite")

    def test_blocks_insert(self, validator):
        sql = "INSERT INTO clients (nom) VALUES ('test')"
        with pytest.raises(SQLSecurityError, match="not allowed"):
            validator.validate(sql, dialect="sqlite")

    def test_blocks_update(self, validator):
        sql = "UPDATE clients SET nom = 'test' WHERE id = 1"
        with pytest.raises(SQLSecurityError, match="not allowed"):
            validator.validate(sql, dialect="sqlite")

    def test_blocks_sqlite_master(self, validator):
        sql = "SELECT * FROM sqlite_master"
        with pytest.raises(SQLSecurityError, match="system table"):
            validator.validate(sql, dialect="sqlite")

    def test_blocks_information_schema(self, validator):
        sql = "SELECT * FROM information_schema.tables"
        with pytest.raises(SQLSecurityError, match="system table"):
            validator.validate(sql, dialect="sqlite")

    def test_blocks_pg_catalog(self, validator):
        sql = "SELECT * FROM pg_catalog.pg_tables"
        with pytest.raises(SQLSecurityError, match="system table"):
            validator.validate(sql, dialect="postgres")

    def test_invalid_syntax_raises(self, validator):
        sql = "SELECT FROM WHERE"
        with pytest.raises(SQLValidationError):
            validator.validate(sql, dialect="sqlite")

    def test_validates_table_references(self, validator, sample_schema):
        sql = "SELECT * FROM nonexistent_table"
        with pytest.raises(SQLValidationError, match="nonexistent_table"):
            validator.validate(sql, dialect="sqlite", schema_info=sample_schema)

    def test_valid_table_reference_passes(self, validator, sample_schema):
        sql = "SELECT id, nom FROM clients"
        result = validator.validate(sql, dialect="sqlite", schema_info=sample_schema)
        assert result is not None

    def test_join_with_valid_tables(self, validator, sample_schema):
        sql = """
        SELECT c.nom, COUNT(o.id) as nb_commandes
        FROM clients c
        LEFT JOIN commandes o ON c.id = o.client_id
        GROUP BY c.nom
        """
        result = validator.validate(sql, dialect="sqlite", schema_info=sample_schema)
        assert result is not None


class TestLimitInjection:
    def test_injects_limit_when_missing(self):
        sql = "SELECT * FROM clients"
        result = SQLValidator.inject_limit(sql, max_rows=500, dialect="sqlite")
        assert "500" in result or "LIMIT" in result.upper()

    def test_preserves_existing_limit(self):
        sql = "SELECT * FROM clients LIMIT 10"
        result = SQLValidator.inject_limit(sql, max_rows=500, dialect="sqlite")
        # Should not change a query that already has LIMIT
        assert "10" in result


class TestAdversarialPayloads:
    """Test that common SQL injection patterns are blocked."""

    adversarial = [
        "SELECT * FROM users; DROP TABLE users;--",
        "SELECT 1 UNION SELECT password FROM users",
        "SELECT * FROM pg_catalog.pg_tables",
        "SELECT * FROM information_schema.columns",
        "DELETE FROM clients",
        "UPDATE clients SET nom='hacked'",
    ]

    @pytest.mark.parametrize("payload", adversarial)
    def test_blocks_adversarial_payload(self, validator, payload):
        with pytest.raises((SQLSecurityError, SQLValidationError)):
            validator.validate(payload, dialect="postgres")
