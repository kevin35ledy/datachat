# Guide — Ajouter un connecteur de base de données

Ce guide permet d'ajouter le support d'un nouveau type de base de données en moins de 4 heures.

## Étape 1 — Créer le fichier connecteur

```python
# backend/app/connectors/your_db.py

from __future__ import annotations
from typing import Any
import yourdb_driver  # Le driver asyncio de votre DB

from app.core.interfaces.connector import AbstractDatabaseConnector
from app.core.models.query import QueryResult, ColumnMeta
from app.core.models.schema import SchemaInfo, TableInfo, ColumnInfo
from app.connectors.base import BaseConnector


class YourDBConnector(BaseConnector):
    """
    Connecteur pour YourDB.

    Connection string format:
        yourdb://user:password@host:port/database
        yourdb:///path/to/local.db  (si fichier local)

    Permissions requises pour le user de connexion:
        SELECT sur toutes les tables cibles

    Dialecte sqlglot: "yourdb"

    Limitations connues:
        - Ne supporte pas les procédures stockées
        - Pas de EXPLAIN détaillé
    """

    def __init__(self, connection_config):
        super().__init__(connection_config)
        self._pool = None

    async def connect(self) -> None:
        """Établit le pool de connexions."""
        self._pool = await yourdb_driver.create_pool(
            dsn=self.connection_config.url,
            min_size=1,
            max_size=10,
        )

    async def disconnect(self) -> None:
        """Ferme proprement le pool."""
        if self._pool:
            await self._pool.close()

    async def test_connection(self) -> bool:
        """Test rapide de connectivité."""
        try:
            async with self._pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception:
            return False

    async def execute_query(
        self,
        sql: str,
        parameters: dict[str, Any] | None = None,
        timeout_seconds: int = 30,
    ) -> QueryResult:
        """
        Exécute un SELECT validé.
        Note: sql a déjà été validé par SQLValidator avant d'arriver ici.
        """
        import time
        start = time.monotonic()

        async with self._pool.acquire() as conn:
            # Adapter selon l'API de votre driver
            rows = await conn.fetch(sql, timeout=timeout_seconds)

        elapsed_ms = int((time.monotonic() - start) * 1000)

        if not rows:
            return QueryResult(
                columns=[], rows=[], total_count=0,
                truncated=False, execution_time_ms=elapsed_ms,
                query_id=self._generate_query_id()
            )

        # Convertir les rows en liste de dicts
        columns = [
            ColumnMeta(name=col, type_name="unknown", type_category="text")
            for col in rows[0].keys()
        ]
        data = [dict(row) for row in rows]

        return QueryResult(
            columns=columns,
            rows=data,
            total_count=len(data),
            truncated=False,  # Le SQLExecutor a déjà injecté un LIMIT
            execution_time_ms=elapsed_ms,
            query_id=self._generate_query_id()
        )

    async def introspect_schema(self) -> SchemaInfo:
        """
        Retourne le schéma complet de la base.
        C'est la méthode la plus importante — sa qualité détermine
        la qualité des requêtes générées par le LLM.
        """
        tables = []

        async with self._pool.acquire() as conn:
            # Récupérer la liste des tables
            table_rows = await conn.fetch("""
                SELECT table_name, table_type
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)

            for table_row in table_rows:
                table_name = table_row['table_name']

                # Récupérer les colonnes
                col_rows = await conn.fetch("""
                    SELECT column_name, data_type, is_nullable,
                           column_default, character_maximum_length
                    FROM information_schema.columns
                    WHERE table_name = $1
                    ORDER BY ordinal_position
                """, table_name)

                columns = [
                    ColumnInfo(
                        name=col['column_name'],
                        type_name=col['data_type'],
                        nullable=col['is_nullable'] == 'YES',
                        default=col['column_default'],
                        is_primary_key=False,  # À remplir avec une requête sur les contraintes
                    )
                    for col in col_rows
                ]

                # Récupérer les FK (adapter selon votre DB)
                fk_rows = await conn.fetch("""
                    SELECT kcu.column_name, ccu.table_name AS ref_table,
                           ccu.column_name AS ref_column
                    FROM information_schema.referential_constraints rc
                    JOIN information_schema.key_column_usage kcu
                        ON rc.constraint_name = kcu.constraint_name
                    JOIN information_schema.constraint_column_usage ccu
                        ON rc.unique_constraint_name = ccu.constraint_name
                    WHERE kcu.table_name = $1
                """, table_name)

                # Compter les lignes approximativement (sans COUNT(*) sur tout)
                try:
                    row_count = await conn.fetchval(
                        f"SELECT COUNT(*) FROM {table_name}"
                    )
                except Exception:
                    row_count = None

                tables.append(TableInfo(
                    name=table_name,
                    columns=columns,
                    row_count=row_count,
                    foreign_keys=[
                        {"column": fk['column_name'],
                         "ref_table": fk['ref_table'],
                         "ref_column": fk['ref_column']}
                        for fk in fk_rows
                    ]
                ))

        return SchemaInfo(
            database_name=self.connection_config.database,
            tables=tables,
            dialect=self.dialect
        )

    async def explain_query(self, sql: str) -> dict[str, Any]:
        """Retourne le plan d'exécution."""
        async with self._pool.acquire() as conn:
            result = await conn.fetch(f"EXPLAIN {sql}")
            return {"plan": [dict(row) for row in result]}

    async def get_table_sample(self, table: str, limit: int = 5) -> QueryResult:
        """Retourne des lignes exemples pour le contexte LLM."""
        return await self.execute_query(
            f"SELECT * FROM {table} LIMIT {limit}"
        )

    @property
    def dialect(self) -> str:
        return "yourdb"  # Nom du dialecte sqlglot pour cette DB

    @property
    def supports_transactions(self) -> bool:
        return True  # Mettre False si votre DB ne supporte pas READ ONLY transactions
```

## Étape 2 — Enregistrer dans le registry

```python
# backend/app/connectors/registry.py — ajouter :

from app.connectors.your_db import YourDBConnector

CONNECTOR_REGISTRY = {
    # ... existants ...
    "yourdb": YourDBConnector,
    "yourdb+async": YourDBConnector,  # Si le driver a un préfixe spécifique
}
```

## Étape 3 — Ajouter les dépendances

```toml
# backend/pyproject.toml — ajouter dans [dependencies] :
yourdb-asyncio = ">=1.0"
```

## Étape 4 — Formulaire frontend

```typescript
// frontend/src/components/connections/ConnectionForm.tsx
// Ajouter dans le switch(dbType) :

case "yourdb":
  return (
    <>
      <FormField name="host" label="Hôte" placeholder="localhost" required />
      <FormField name="port" label="Port" type="number" defaultValue="5432" />
      <FormField name="database" label="Base de données" required />
      <FormField name="username" label="Utilisateur" required />
      <FormField name="password" label="Mot de passe" type="password" required />
      // Champs spécifiques à votre DB si nécessaire
    </>
  );
```

## Étape 5 — Tests

```python
# backend/tests/integration/test_connectors.py

@pytest.mark.asyncio
async def test_yourdb_connector():
    """Test avec une instance de test de votre DB."""
    config = ConnectionConfig(url="yourdb://test:test@localhost/test_db")
    connector = YourDBConnector(config)

    await connector.connect()

    # Test de connectivité
    assert await connector.test_connection() is True

    # Test d'introspection schéma
    schema = await connector.introspect_schema()
    assert len(schema.tables) > 0

    # Test d'exécution
    result = await connector.execute_query("SELECT 1 AS test_value")
    assert result.rows[0]["test_value"] == 1

    # Test de sample
    if schema.tables:
        sample = await connector.get_table_sample(schema.tables[0].name, limit=3)
        assert len(sample.rows) <= 3

    await connector.disconnect()
```

## Checklist avant PR

- [ ] Les 7 méthodes du Protocol sont implémentées
- [ ] Le format de connection string est documenté dans la docstring de la classe
- [ ] `introspect_schema()` retourne les FK si le DB les supporte
- [ ] `get_table_sample()` ne retourne pas plus de `limit` lignes
- [ ] Gestion propre des erreurs de connexion (pas de crash non géré)
- [ ] `disconnect()` ferme proprement le pool même si `connect()` a échoué
- [ ] Tests d'intégration passent
- [ ] Driver ajouté dans `pyproject.toml`
- [ ] Enregistré dans `registry.py`
- [ ] Formulaire frontend mis à jour
- [ ] "Limitations connues" documentées dans la docstring
