from __future__ import annotations
from typing import Any, TYPE_CHECKING
from sqlalchemy import text as sa_text
from app.connectors.base import BaseConnector, _infer_type_category
from app.core.models.schema import SchemaInfo, TableInfo, ColumnInfo, ForeignKey, IndexInfo
from app.core.models.query import QueryResult

if TYPE_CHECKING:
    from app.config import Settings
    from app.core.models.connection import ConnectionConfig


class SQLiteConnector(BaseConnector):
    """
    Connector for SQLite databases.

    Connection string formats:
        sqlite+aiosqlite:///path/to/file.db
        sqlite+aiosqlite:///:memory:

    Permissions: N/A (file-based, use OS permissions)

    sqlglot dialect: sqlite

    Known limitations:
        - No EXPLAIN ANALYZE (only EXPLAIN QUERY PLAN)
        - No server-side row-level security
        - No native READ ONLY transaction (enforced via read-only file open)
        - Limited data types (everything maps to affinity types)
    """

    def __init__(self, config: "ConnectionConfig", settings: "Settings"):
        super().__init__(config, settings)

    def _async_url(self) -> str:
        url = self.config.url
        # Ensure aiosqlite driver
        if url.startswith("sqlite://") and "+aiosqlite" not in url:
            url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)
        return url

    async def introspect_schema(self) -> SchemaInfo:
        tables = []
        async with self._engine.connect() as conn:
            # Get all user tables (exclude internal SQLite tables)
            table_rows = await conn.execute(
                sa_text(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                    "ORDER BY name"
                )
            )
            table_names = [row[0] for row in table_rows.fetchall()]

            for table_name in table_names:
                # Get column info via PRAGMA
                col_rows = await conn.execute(
                    sa_text(f"PRAGMA table_info('{table_name}')")
                )
                cols_raw = col_rows.fetchall()

                columns = []
                for col in cols_raw:
                    # PRAGMA table_info columns: cid, name, type, notnull, dflt_value, pk
                    columns.append(
                        ColumnInfo(
                            name=col[1],
                            type_name=col[2] or "TEXT",
                            nullable=col[3] == 0,
                            default=col[4],
                            is_primary_key=col[5] > 0,
                        )
                    )

                # Get foreign keys via PRAGMA
                fk_rows = await conn.execute(
                    sa_text(f"PRAGMA foreign_key_list('{table_name}')")
                )
                foreign_keys = []
                for fk in fk_rows.fetchall():
                    # id, seq, table, from, to, on_update, on_delete, match
                    foreign_keys.append(
                        ForeignKey(
                            column=fk[3],
                            ref_table=fk[2],
                            ref_column=fk[4],
                        )
                    )
                # Mark FK columns
                fk_col_names = {fk.column for fk in foreign_keys}
                for col in columns:
                    if col.name in fk_col_names:
                        col.is_foreign_key = True

                # Get indexes
                idx_rows = await conn.execute(
                    sa_text(f"PRAGMA index_list('{table_name}')")
                )
                indexes = []
                for idx in idx_rows.fetchall():
                    # seq, name, unique, origin, partial
                    idx_info = await conn.execute(
                        sa_text(f"PRAGMA index_info('{idx[1]}')")
                    )
                    idx_cols = [r[2] for r in idx_info.fetchall()]
                    indexes.append(
                        IndexInfo(
                            name=idx[1],
                            columns=idx_cols,
                            unique=bool(idx[2]),
                        )
                    )

                # Approximate row count
                try:
                    cnt = await conn.execute(sa_text(f"SELECT COUNT(*) FROM '{table_name}'"))
                    row_count = cnt.scalar()
                except Exception:
                    row_count = None

                tables.append(
                    TableInfo(
                        name=table_name,
                        schema_name="main",
                        columns=columns,
                        foreign_keys=foreign_keys,
                        indexes=indexes,
                        row_count=row_count,
                    )
                )

        return SchemaInfo(
            database_name=self.config.database or "main",
            dialect=self.dialect,
            tables=tables,
        )

    async def explain_query(self, sql: str) -> dict[str, Any]:
        async with self._engine.connect() as conn:
            rows = await conn.execute(sa_text(f"EXPLAIN QUERY PLAN {sql}"))
            return {"plan": [dict(row._mapping) for row in rows.fetchall()]}

    @property
    def dialect(self) -> str:
        return "sqlite"

    @property
    def supports_transactions(self) -> bool:
        return False  # SQLite doesn't have server-side READ ONLY transactions
