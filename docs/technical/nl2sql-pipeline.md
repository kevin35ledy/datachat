# Pipeline NL→SQL — Référence technique

## Vue d'ensemble

Le pipeline NL→SQL est le cœur de DB-IA. Il transforme une question en langage naturel en résultats de base de données. Voir [architecture/data-flow.md](../architecture/data-flow.md) pour le diagramme de séquence.

## Étape 1 — Schema RAG

**Module** : `backend/app/services/schema/embedder.py` + `backend/app/vector_store/qdrant_store.py`

### Comment ça marche

Pour chaque table, un document descriptif est créé et stocké dans Qdrant :

```
Table: commandes
Description: Enregistre les commandes des clients.
Colonnes:
  - id (INTEGER, PK) : identifiant unique de la commande
  - client_id (INTEGER, FK→clients.id) : client qui a passé la commande
  - date_commande (DATE) : date à laquelle la commande a été passée
  - montant_total (DECIMAL(10,2)) : montant total TTC
  - statut (VARCHAR) : état de la commande (en_attente, validée, expédiée, annulée)
  - adresse_livraison (TEXT) : adresse complète de livraison
```

À chaque requête :
1. La requête NL est embedée : `embed("Top 10 clients par CA ce trimestre")`
2. Qdrant retourne les k tables les plus proches par similarité cosinus
3. Par défaut k=10, max k=20 (configurable)

### Bypass automatique

Si la base a moins de `SCHEMA_RAG_MIN_TABLES` tables (défaut: 20), le schéma complet est envoyé sans passer par Qdrant.

### Refresh des embeddings

```python
# Déclenché automatiquement :
# - À la première connexion à une base
# - Quand un schema drift est détecté
# - Via job Celery périodique (toutes les 24h par défaut)

@celery_app.task
async def refresh_schema_embeddings(conn_id: str): ...
```

---

## Étape 2 — Prompt Assembly

**Module** : `backend/app/services/nl2sql/prompt_builder.py`

### Structure du prompt

```
SYSTEM:
  Tu es un expert SQL. Génère uniquement du SQL valide et sûr.

  Règles impératives:
  - Génère uniquement des requêtes SELECT
  - N'accède pas aux tables système (information_schema, pg_catalog, etc.)
  - Si tu ne peux pas répondre avec les tables disponibles, dis-le clairement
  - Inclus toujours un LIMIT si la requête peut retourner beaucoup de lignes

  Dialecte cible: {dialect}
  Base de données: {db_name}

SCHÉMA (tables pertinentes):
  {schema_context}  ← top-k tables depuis le RAG

EXEMPLES (few-shot, optionnel):
  Question: "Combien de clients avons-nous ?"
  SQL: SELECT COUNT(*) AS nb_clients FROM clients;

  Question: "Quels sont les produits les plus vendus ?"
  SQL: SELECT p.nom, COUNT(l.id) AS nb_ventes
       FROM lignes_commandes l JOIN produits p ON l.produit_id = p.id
       GROUP BY p.nom ORDER BY nb_ventes DESC LIMIT 10;

HISTORIQUE DE CONVERSATION:
  User: "Montre-moi les clients de Paris"
  Assistant: SELECT * FROM clients WHERE ville = 'Paris';
  [SQL exécuté, 47 résultats]

  User: "Et parmi eux, lesquels ont commandé ce mois ?"
  → [question actuelle — doit utiliser le contexte "clients de Paris"]

USER:
  {nl_query}

FORMAT DE RÉPONSE ATTENDU:
  <sql>
  SELECT ...
  </sql>
  <explanation>
  Cette requête... [explication en 1-2 phrases]
  </explanation>
  <confidence>0.95</confidence>
```

### Gestion du budget de tokens

```python
PROMPT_TOKEN_BUDGET = {
    "system": 500,
    "schema": 4000,      # La partie la plus variable
    "examples": 800,
    "history": 1500,     # N derniers échanges
    "user_query": 200,
    "response_reserved": 1000
}
# Total max: ~8000 tokens (compatible tous modèles)
```

Si le schéma dépasse le budget, le nombre de tables RAG est réduit.

---

## Étape 3 — LLM Generation

**Module** : `backend/app/llm/base.py`

```python
response = await llm_provider.complete(LLMRequest(
    messages=[{"role": "user", "content": assembled_prompt}],
    temperature=0.1,      # Faible pour reproductibilité SQL
    max_tokens=1000,
))
```

`temperature=0.1` est critique : un temperature élevé produit du SQL créatif mais incorrect.

---

## Étapes 4-8 — Validation

**Module** : `backend/app/services/nl2sql/sql_validator.py`

### Étape 4 : Extraction du SQL

```python
def extract_sql(llm_response: str) -> str:
    # Priorité 1 : balises <sql></sql>
    match = re.search(r'<sql>(.*?)</sql>', response, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Priorité 2 : bloc de code markdown ```sql ... ```
    match = re.search(r'```sql\n(.*?)```', response, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Priorité 3 : texte brut (risqué, mais dernier recours)
    raise SQLExtractionError("Could not extract SQL from LLM response")
```

### Étape 5 : Parsing AST

```python
import sqlglot

try:
    ast = sqlglot.parse_one(raw_sql, dialect=target_dialect)
except sqlglot.errors.ParseError as e:
    raise SQLValidationError(f"SQL syntax error: {e}")
```

### Étape 6 : Safety Gate

```python
ALLOWED_STATEMENT_TYPES = {sqlglot.expressions.Select}
BLOCKED_SYSTEM_PREFIXES = [
    "information_schema", "pg_catalog", "pg_",
    "mysql", "sys", "performance_schema",
    "sqlite_master", "sqlite_sequence"
]

# Vérification du type de statement
if type(ast) not in ALLOWED_STATEMENT_TYPES:
    raise SQLSecurityError(
        f"Statement type {type(ast).__name__} is not allowed. Only SELECT is permitted."
    )

# Vérification des tables référencées
for table in ast.find_all(sqlglot.expressions.Table):
    if any(table.name.lower().startswith(p) for p in BLOCKED_SYSTEM_PREFIXES):
        raise SQLSecurityError(f"Access to system table '{table.name}' is not allowed.")
```

### Étape 7 : Validation des références

```python
# Toutes les tables et colonnes référencées doivent exister dans le SchemaInfo
referenced_tables = {t.name for t in ast.find_all(sqlglot.expressions.Table)}
known_tables = {t.name for t in schema_info.tables}

unknown = referenced_tables - known_tables
if unknown:
    raise SQLValidationError(f"Unknown tables referenced: {unknown}")
```

### Étape 8 : Transpilation de dialecte

```python
# sqlglot normalise le SQL vers le dialecte cible
validated_sql = sqlglot.transpile(
    raw_sql,
    read="auto",           # Auto-détection du dialecte source
    write=target_dialect,  # Dialecte cible du connecteur
    pretty=True            # SQL lisible
)[0]
```

---

## Étape 9 — Execution

**Module** : `backend/app/services/nl2sql/sql_executor.py`

```python
async def execute_safe(
    validated_sql: str,
    connector: AbstractDatabaseConnector,
    max_rows: int = 1000,
    timeout: int = 30
) -> QueryResult:
    # Injection du LIMIT si absent
    sql_with_limit = inject_limit_if_missing(validated_sql, max_rows)

    # Exécution dans une transaction READ ONLY si supportée
    if connector.supports_transactions:
        async with connector.readonly_transaction():
            return await connector.execute_query(sql_with_limit, timeout_seconds=timeout)
    else:
        return await connector.execute_query(sql_with_limit, timeout_seconds=timeout)
```

---

## Étape 10 — Result Formatting

**Module** : `backend/app/services/nl2sql/result_formatter.py`

### Inférence du type de graphique

```python
def infer_chart_type(columns: list[ColumnMeta], row_count: int) -> ChartSuggestion | None:
    col_types = [c.type_category for c in columns]  # "numeric", "text", "date", "boolean"

    if row_count < 2:
        return None  # Pas assez de points pour un graphique

    if col_types == ["text", "numeric"]:
        return ChartSuggestion(type="bar", x=columns[0].name, y=columns[1].name)

    if col_types == ["date", "numeric"]:
        return ChartSuggestion(type="line", x=columns[0].name, y=columns[1].name)

    if col_types == ["numeric", "numeric"]:
        return ChartSuggestion(type="scatter", x=columns[0].name, y=columns[1].name)

    # Plus d'une colonne numérique + une catégorie → barres groupées
    if col_types[0] == "text" and all(t == "numeric" for t in col_types[1:]):
        return ChartSuggestion(type="bar_grouped", ...)

    return None
```

### Résumé NL

Un deuxième appel LLM (modèle léger : Haiku) génère un résumé en 1-2 phrases :

```python
summary = await llm_provider.complete(LLMRequest(
    model="claude-haiku-4-5-20251001",
    messages=[{
        "role": "user",
        "content": f"""
        Question: {nl_query}
        SQL exécuté: {validated_sql}
        Résultats: {result.rows[:5]} (sur {result.total_count} total)

        Résume en 1-2 phrases en français ce que montrent ces résultats.
        """
    }],
    max_tokens=150,
    temperature=0.3
))
```

---

## Gestion des cas limites

| Cas | Comportement |
|-----|-------------|
| LLM génère plusieurs statements | Seul le premier est conservé |
| Requête sans résultats | Retourne `{rows: [], total_count: 0}` + message "Aucun résultat trouvé" |
| Résultat tronqué (LIMIT) | `truncated: true` + warning affiché dans l'UI |
| Timeout DB | `QueryTimeoutError` → message "Requête trop longue, affinez votre question" |
| Faible confiance LLM (<0.6) | Warning affiché dans l'UI : "Résultat incertain — vérifiez le SQL" |
