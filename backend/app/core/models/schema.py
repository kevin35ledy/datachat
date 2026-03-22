from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


class ForeignKey(BaseModel):
    """A foreign key relationship."""

    column: str
    ref_table: str
    ref_column: str
    constraint_name: str = ""


class IndexInfo(BaseModel):
    """Index metadata."""

    name: str
    columns: list[str]
    unique: bool = False
    primary: bool = False


class ColumnInfo(BaseModel):
    """Metadata for a single column."""

    name: str
    type_name: str
    nullable: bool = True
    default: Any = None
    is_primary_key: bool = False
    is_foreign_key: bool = False
    comment: str = ""


class TableInfo(BaseModel):
    """Metadata for a single table."""

    name: str
    schema_name: str = "public"
    columns: list[ColumnInfo] = Field(default_factory=list)
    foreign_keys: list[ForeignKey] = Field(default_factory=list)
    indexes: list[IndexInfo] = Field(default_factory=list)
    row_count: int | None = None
    comment: str = ""

    @property
    def column_names(self) -> list[str]:
        return [c.name for c in self.columns]

    @property
    def pk_columns(self) -> list[str]:
        return [c.name for c in self.columns if c.is_primary_key]


class SchemaInfo(BaseModel):
    """Complete schema metadata for a database connection."""

    database_name: str
    dialect: str
    tables: list[TableInfo] = Field(default_factory=list)
    introspected_at: str = ""

    @property
    def table_names(self) -> list[str]:
        return [t.name for t in self.tables]

    def get_table(self, name: str) -> TableInfo | None:
        for t in self.tables:
            if t.name.lower() == name.lower():
                return t
        return None

    def to_prompt_context(self, tables: list[str] | None = None) -> str:
        """Serialize selected tables to a human-readable string for LLM prompts."""
        target = [t for t in self.tables if tables is None or t.name in tables]
        lines = []
        for table in target:
            cols = ", ".join(
                f"{c.name} ({c.type_name}{'  PK' if c.is_primary_key else ''}{'  NOT NULL' if not c.nullable else ''})"
                for c in table.columns
            )
            fks = ""
            if table.foreign_keys:
                fk_parts = [f"{fk.column} → {fk.ref_table}.{fk.ref_column}" for fk in table.foreign_keys]
                fks = f"\n  FK: {', '.join(fk_parts)}"
            row_info = f" (~{table.row_count:,} rows)" if table.row_count else ""
            lines.append(f"Table: {table.name}{row_info}\n  Columns: {cols}{fks}")
        return "\n\n".join(lines)
