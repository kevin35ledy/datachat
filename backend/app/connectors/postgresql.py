from __future__ import annotations
from typing import Any, TYPE_CHECKING
from sqlalchemy import text as sa_text
from app.connectors.base import BaseConnector, _infer_type_category
from app.core.models.schema import SchemaInfo, TableInfo, ColumnInfo, ForeignKey, IndexInfo
from app.core.models.query import QueryResult

if TYPE_CHECKING:
    from app.config import Settings
    from app.core.models.connection import ConnectionConfig


class PostgreSQLConnector(BaseConnector):
    """
    Connector for PostgreSQL databases (13+).

    Connection string formats:
        postgresql+asyncpg://user:password@host:5432/database
        postgresql+asyncpg://user:password@host:5432/database?ssl=require

    Recommended user permissions:
        GRANT CONNECT ON DATABASE mydb TO dbia_query;
        GRANT USAGE ON SCHEMA public TO dbia_query;
        GRANT SELECT ON ALL TABLES IN SCHEMA public TO dbia_query;

    sqlglot dialect: postgres

    Known limitations:
        - pg_stat_statements extension must be enabled for slow query analysis
        - Row-level security policies are checked but not enforced via this connector
    """

    def __init__(self, config: "ConnectionConfig", settings: "Settings"):
        super().__init__(config, settings)

    def _async_url(self) -> str:
        url = self.config.url
        if url.startswith("postgresql://") and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("postgres://") and "+asyncpg" not in url:
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url

    async def execute_query(
        self,
        sql: str,
        parameters: dict[str, Any] | None = None,
        timeout_seconds: int = 30,
    ) -> QueryResult:
        import time, uuid
        from app.core.models.query import ColumnMeta
        from sqlalchemy import text as sa_text

        start = time.monotonic()
        async with self._engine.connect() as conn:
            # Execute in a read-only transaction
            await conn.execute(sa_text("BEGIN READ ONLY"))
            try:
                result = await conn.execute(sa_text(sql), parameters or {})
                rows_raw = result.fetchall()
                col_names = list(result.keys())
                # Get type OIDs for better type inference
                col_types = [str(col.type) for col in result.cursor.description] if result.cursor else []
            finally:
                await conn.execute(sa_text("ROLLBACK"))

        elapsed_ms = int((time.monotonic() - start) * 1000)
        columns = [
            ColumnMeta(
                name=name,
                type_name=col_types[i] if i < len(col_types) else "unknown",
                type_category=_infer_type_category(col_types[i] if i < len(col_types) else ""),
            )
            for i, name in enumerate(col_names)
        ]
        rows = [dict(zip(col_names, row)) for row in rows_raw]
        return QueryResult(
            query_id=str(uuid.uuid4()),
            columns=columns,
            rows=rows,
            total_count=len(rows),
            truncated=False,
            execution_time_ms=elapsed_ms,
        )

    async def introspect_schema(self) -> SchemaInfo:
        schema_name = self.config.schema_name or "public"
        tables = []

        async with self._engine.connect() as conn:
            # Tables
            table_rows = await conn.execute(sa_text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = :schema AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """), {"schema": schema_name})
            table_names = [r[0] for r in table_rows.fetchall()]

            for table_name in table_names:
                # Columns
                col_rows = await conn.execute(sa_text("""
                    SELECT
                        c.column_name, c.data_type, c.is_nullable, c.column_default,
                        c.character_maximum_length,
                        CASE WHEN pk.column_name IS NOT NULL THEN true ELSE false END as is_pk
                    FROM information_schema.columns c
                    LEFT JOIN (
                        SELECT ku.column_name
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage ku
                            ON tc.constraint_name = ku.constraint_name
                            AND tc.table_schema = ku.table_schema
                        WHERE tc.constraint_type = 'PRIMARY KEY'
                          AND tc.table_name = :table AND tc.table_schema = :schema
                    ) pk ON c.column_name = pk.column_name
                    WHERE c.table_name = :table AND c.table_schema = :schema
                    ORDER BY c.ordinal_position
                """), {"table": table_name, "schema": schema_name})

                columns = [
                    ColumnInfo(
                        name=r[0],
                        type_name=r[1],
                        nullable=r[2] == "YES",
                        default=r[3],
                        is_primary_key=bool(r[5]),
                    )
                    for r in col_rows.fetchall()
                ]

                # Foreign keys
                fk_rows = await conn.execute(sa_text("""
                    SELECT
                        kcu.column_name,
                        ccu.table_name AS ref_table,
                        ccu.column_name AS ref_column,
                        tc.constraint_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                        ON tc.constraint_name = kcu.constraint_name
                    JOIN information_schema.constraint_column_usage ccu
                        ON tc.constraint_name = ccu.constraint_name
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                      AND tc.table_name = :table AND tc.table_schema = :schema
                """), {"table": table_name, "schema": schema_name})

                foreign_keys = [
                    ForeignKey(
                        column=r[0], ref_table=r[1], ref_column=r[2], constraint_name=r[3]
                    )
                    for r in fk_rows.fetchall()
                ]
                fk_col_names = {fk.column for fk in foreign_keys}
                for col in columns:
                    if col.name in fk_col_names:
                        col.is_foreign_key = True

                # Indexes
                idx_rows = await conn.execute(sa_text("""
                    SELECT
                        i.relname as index_name,
                        array_agg(a.attname ORDER BY ix.indkey_subscript) as column_names,
                        ix.indisunique,
                        ix.indisprimary
                    FROM pg_class t
                    JOIN pg_index ix ON t.oid = ix.indrelid
                    JOIN pg_class i ON i.oid = ix.indexrelid
                    JOIN pg_namespace n ON n.oid = t.relnamespace
                    JOIN LATERAL unnest(ix.indkey) WITH ORDINALITY AS ik(attnum, indkey_subscript)
                        ON TRUE
                    JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ik.attnum
                    WHERE t.relname = :table AND n.nspname = :schema
                    GROUP BY i.relname, ix.indisunique, ix.indisprimary
                """), {"table": table_name, "schema": schema_name})

                indexes = [
                    IndexInfo(
                        name=r[0],
                        columns=list(r[1]) if r[1] else [],
                        unique=bool(r[2]),
                        primary=bool(r[3]),
                    )
                    for r in idx_rows.fetchall()
                ]

                # Row count (estimate from pg_class for speed)
                try:
                    cnt = await conn.execute(sa_text("""
                        SELECT reltuples::bigint FROM pg_class
                        WHERE relname = :table
                    """), {"table": table_name})
                    row_count = cnt.scalar() or 0
                except Exception:
                    row_count = None

                tables.append(TableInfo(
                    name=table_name,
                    schema_name=schema_name,
                    columns=columns,
                    foreign_keys=foreign_keys,
                    indexes=indexes,
                    row_count=row_count,
                ))

        return SchemaInfo(
            database_name=self.config.database,
            dialect=self.dialect,
            tables=tables,
        )

    async def explain_query(self, sql: str) -> dict[str, Any]:
        async with self._engine.connect() as conn:
            rows = await conn.execute(sa_text(f"EXPLAIN (FORMAT JSON) {sql}"))
            result = rows.fetchone()
            return {"plan": result[0] if result else {}}

    @property
    def dialect(self) -> str:
        return "postgres"

    @property
    def supports_transactions(self) -> bool:
        return True
