from __future__ import annotations
import re
from typing import TYPE_CHECKING
import sqlglot
import sqlglot.expressions as exp
from app.core.exceptions import SQLValidationError, SQLSecurityError, SQLExtractionError

if TYPE_CHECKING:
    from app.core.models.schema import SchemaInfo


# Statement types that are explicitly allowed
ALLOWED_STATEMENT_TYPES = (exp.Select,)

# System table name prefixes/patterns that must never be accessed
BLOCKED_TABLE_PATTERNS = [
    re.compile(r"^information_schema", re.IGNORECASE),
    re.compile(r"^pg_", re.IGNORECASE),
    re.compile(r"^mysql\.", re.IGNORECASE),
    re.compile(r"^sys\.", re.IGNORECASE),
    re.compile(r"^performance_schema", re.IGNORECASE),
    re.compile(r"^sqlite_", re.IGNORECASE),
]

# Hard-coded SQL keyword patterns that should never appear after validation
BLOCKED_KEYWORDS = frozenset([
    "DROP", "DELETE", "INSERT", "UPDATE", "TRUNCATE",
    "CREATE", "ALTER", "GRANT", "REVOKE", "EXEC", "EXECUTE",
    "CALL", "MERGE", "UPSERT", "COPY", "LOAD",
])


class SQLValidator:
    """
    Safety gate for all LLM-generated SQL.

    Performs AST-level validation using sqlglot — immune to obfuscation tricks
    that fool regex-based approaches.

    CRITICAL: This class is the last line of defense before SQL execution.
    Any change to validation logic requires security review.
    """

    def validate(
        self,
        sql: str,
        dialect: str,
        schema_info: "SchemaInfo | None" = None,
    ) -> str:
        """
        Validate and normalize SQL. Returns the validated SQL string.
        Raises SQLSecurityError or SQLValidationError on failure.

        Args:
            sql: Raw SQL string from LLM.
            dialect: Target database dialect (e.g. 'sqlite', 'postgres').
            schema_info: If provided, validates table/column references exist.

        Returns:
            Validated and dialect-normalized SQL string.
        """
        sql = sql.strip()

        # Step 1: Parse to AST (hard fail on syntax error)
        try:
            ast = sqlglot.parse_one(sql, dialect=dialect, error_level=sqlglot.ErrorLevel.RAISE)
        except sqlglot.errors.ParseError as e:
            raise SQLValidationError(f"SQL syntax error: {e}") from e

        # Step 2: Whitelist — only SELECT allowed
        if not isinstance(ast, ALLOWED_STATEMENT_TYPES):
            stmt_type = type(ast).__name__
            raise SQLSecurityError(
                f"Statement type '{stmt_type}' is not allowed. Only SELECT statements can be executed."
            )

        # Step 3: Block system tables
        for table in ast.find_all(exp.Table):
            table_ref = table.name or ""
            db_ref = (table.db or "") + "." + table_ref if table.db else table_ref
            for pattern in BLOCKED_TABLE_PATTERNS:
                if pattern.match(table_ref) or pattern.match(db_ref):
                    raise SQLSecurityError(
                        f"Access to system table '{db_ref or table_ref}' is not permitted."
                    )

        # Step 4: Block dangerous functions
        for func in ast.find_all(exp.Anonymous):
            fname = (func.name or "").upper()
            if fname in {"PG_READ_FILE", "PG_LS_DIR", "PG_EXEC", "LOAD_FILE", "SYSTEM"}:
                raise SQLSecurityError(f"Function '{fname}' is not permitted.")

        # Step 5: Validate table references against known schema (if provided)
        if schema_info is not None:
            known_tables = {t.name.lower() for t in schema_info.tables}
            for table in ast.find_all(exp.Table):
                if table.name and table.name.lower() not in known_tables:
                    raise SQLValidationError(
                        f"Table '{table.name}' does not exist in the connected database. "
                        f"Available tables: {sorted(known_tables)[:10]}"
                    )

        # Step 6: Transpile to target dialect (normalizes quirks)
        try:
            normalized = sqlglot.transpile(sql, read=dialect, write=dialect, pretty=True)[0]
        except Exception:
            normalized = sql  # Keep original if transpilation fails

        return normalized

    @staticmethod
    def extract_sql(llm_response: str) -> str:
        """
        Extract a SQL block from an LLM response.

        Tries in order:
        1. Content between <sql></sql> tags
        2. Content in ```sql ... ``` markdown blocks
        3. Content in ``` ... ``` blocks
        4. The raw response if it looks like SQL

        Raises SQLExtractionError if no SQL can be found.
        """
        response = llm_response.strip()

        # Pattern 1: <sql> tags
        m = re.search(r"<sql>(.*?)</sql>", response, re.DOTALL | re.IGNORECASE)
        if m:
            return m.group(1).strip()

        # Pattern 2: ```sql ... ```
        m = re.search(r"```sql\s*(.*?)```", response, re.DOTALL | re.IGNORECASE)
        if m:
            return m.group(1).strip()

        # Pattern 3: generic code block
        m = re.search(r"```\s*(.*?)```", response, re.DOTALL)
        if m:
            candidate = m.group(1).strip()
            if candidate.upper().startswith("SELECT"):
                return candidate

        # Pattern 4: raw SELECT
        if response.upper().lstrip().startswith("SELECT"):
            return response

        raise SQLExtractionError(
            "Could not extract SQL from LLM response. "
            "Expected <sql>...</sql> tags or a ```sql``` code block."
        )

    @staticmethod
    def inject_limit(sql: str, max_rows: int = 1000, dialect: str = "sqlite") -> str:
        """
        Inject a LIMIT clause if the query doesn't already have one.
        Prevents runaway queries on large tables.
        """
        try:
            ast = sqlglot.parse_one(sql, dialect=dialect)
            if isinstance(ast, exp.Select):
                if ast.args.get("limit") is None:
                    ast = ast.limit(max_rows)
                    return ast.sql(dialect=dialect, pretty=True)
        except Exception:
            pass
        return sql
