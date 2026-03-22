# Connecteurs de bases de données

## Architecture

Tous les connecteurs implémentent le Protocol `AbstractDatabaseConnector` défini dans `backend/app/core/interfaces/connector.py`. Un `ConnectorRegistry` mappe les préfixes de connection string vers les classes d'implémentation.

```python
# backend/app/connectors/registry.py
CONNECTOR_REGISTRY = {
    "postgresql": PostgreSQLConnector,
    "postgres":   PostgreSQLConnector,
    "mysql":      MySQLConnector,
    "mariadb":    MySQLConnector,
    "sqlite":     SQLiteConnector,
    "csv":        CSVConnector,
    "mongodb":    MongoDBConnector,
    "bigquery":   BigQueryConnector,
}

def get_connector(connection_config: ConnectionConfig) -> AbstractDatabaseConnector:
    scheme = connection_config.url.split("://")[0].lower()
    cls = CONNECTOR_REGISTRY.get(scheme)
    if not cls:
        raise UnsupportedDatabaseError(f"Unsupported database type: {scheme}")
    return cls(connection_config)
```

## Connecteurs supportés

### PostgreSQL (Phase 1)

**Driver** : `asyncpg`
**sqlglot dialect** : `"postgres"`
**Connection string** : `postgresql://user:password@host:5432/database`

Fonctionnalités spécifiques :
- Introspection complète via `information_schema` + `pg_catalog`
- FK relationships via `pg_constraint`
- `EXPLAIN ANALYZE` pour les plans d'exécution
- `pg_stat_statements` pour les slow queries (si extension activée)
- Transactions `BEGIN READ ONLY` / `ROLLBACK`
- Support des schémas (non juste `public`)

Configuration minimale du user :
```sql
CREATE USER dbia_query WITH PASSWORD 'xxx';
GRANT CONNECT ON DATABASE mydb TO dbia_query;
GRANT USAGE ON SCHEMA public TO dbia_query;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO dbia_query;
```

### SQLite (Phase 1)

**Driver** : `aiosqlite`
**sqlglot dialect** : `"sqlite"`
**Connection string** : `sqlite:///path/to/database.db` ou `sqlite:///:memory:`

Fonctionnalités spécifiques :
- Introspection via `sqlite_master`
- FK relationships via `PRAGMA foreign_key_list`
- Pas de transactions READ ONLY natives — émulé par user sans droits d'écriture
- Idéal pour dev/tests : pas d'infrastructure

Limitations :
- Pas de `EXPLAIN` détaillé (EXPLAIN QUERY PLAN seulement)
- Pas de statistiques sur les colonnes
- Concurrent reads seulement (pas de writes de toute façon)

### MySQL / MariaDB (Phase 2)

**Driver** : `aiomysql`
**sqlglot dialect** : `"mysql"`
**Connection string** : `mysql://user:password@host:3306/database`

Fonctionnalités spécifiques :
- Introspection via `information_schema`
- FK via `KEY_COLUMN_USAGE`
- `EXPLAIN FORMAT=JSON` pour les plans
- Slow query log via `performance_schema.events_statements_summary_by_digest`
- `START TRANSACTION READ ONLY` pour les requêtes NL

### CSV (Phase 2)

**Driver** : DuckDB (in-process)
**sqlglot dialect** : `"duckdb"`
**Connection string** : `csv:///path/to/directory` ou `csv:///path/to/file.csv`

Fonctionnalités spécifiques :
- DuckDB lit les CSV directement comme des tables SQL
- Auto-détection des types (INT, FLOAT, VARCHAR, DATE)
- Support multi-fichiers : chaque fichier CSV devient une "table"
- Pas de FK (fichiers plats)
- Idéal pour analyse ad-hoc de fichiers de données

Limitations :
- Lecture seule (pas d'écriture dans les CSV)
- Pas de contraintes
- Performance dépend de la taille du fichier

### MongoDB (Phase 4)

**Driver** : `motor` (asyncio)
**sqlglot dialect** : N/A — requêtes en MQL ou pipeline d'agrégation
**Connection string** : `mongodb://user:password@host:27017/database`

Note importante : MongoDB ne parle pas SQL. Le LLM génère des pipelines d'agrégation MongoDB JSON plutôt que du SQL. Le `SQLValidator` est remplacé par un `MQLValidator` pour ce connecteur.

Fonctionnalités spécifiques :
- Introspection de schéma par sampling (MongoDB est schemaless)
- Pipelines d'agrégation `$match`, `$group`, `$sort`, `$limit`
- Pas de JOINs natifs (lookup disponible)

### BigQuery (Phase 4)

**Driver** : `google-cloud-bigquery`
**sqlglot dialect** : `"bigquery"`
**Connection string** : `bigquery://project-id/dataset`

Fonctionnalités spécifiques :
- Auth via Google Application Default Credentials
- Introspection via `INFORMATION_SCHEMA`
- `EXPLAIN` via dry-run (estimation des bytes scannés)
- Coût estimé avant exécution (bytes scanned → $ estimé)
- Partitionnement et clustering pris en compte dans les suggestions

---

## Interface AbstractDatabaseConnector

```python
class AbstractDatabaseConnector(Protocol):

    async def connect(self) -> None:
        """Établit le pool de connexions. Appelé une fois au démarrage."""

    async def disconnect(self) -> None:
        """Ferme proprement toutes les connexions."""

    async def test_connection(self) -> bool:
        """Vérifie la connectivité sans effets de bord."""

    async def execute_query(
        self,
        sql: str,
        parameters: dict | None = None,
        timeout_seconds: int = 30
    ) -> QueryResult:
        """Exécute un SELECT validé et retourne le résultat structuré."""

    async def introspect_schema(self) -> SchemaInfo:
        """Retourne le schéma complet : tables, colonnes, types, FK, index."""

    async def explain_query(self, sql: str) -> dict:
        """Retourne le plan d'exécution natif de la base."""

    async def get_table_sample(self, table: str, limit: int = 5) -> QueryResult:
        """Retourne des lignes exemples pour le contexte des prompts."""

    @property
    def dialect(self) -> str:
        """Nom du dialecte sqlglot : 'postgres', 'mysql', 'sqlite', etc."""

    @property
    def supports_transactions(self) -> bool:
        """True si le connecteur supporte les transactions READ ONLY."""
```

---

## Guide d'ajout d'un nouveau connecteur

Voir [guides/add-db-connector.md](../guides/add-db-connector.md) pour le guide pas-à-pas avec template de code.
