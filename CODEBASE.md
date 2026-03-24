# CODEBASE.md — Référence complète DataChat

> Fichier de référence technique maintenu à jour. Lire ce fichier suffit pour travailler sur n'importe quelle partie du projet sans ré-explorer le code.

---

## Structure du projet

```
database_ia/
├── CLAUDE.md                    # Vision, architecture, conventions (référence permanente)
├── CODEBASE.md                  # Ce fichier — inventaire technique détaillé
├── Makefile                     # Commandes dev (infra/backend/frontend/test)
├── docker-compose.yml           # Redis + Qdrant + API + Worker (profiles: full)
├── .env                         # Variables d'environnement locales (non versionné)
├── .env.example                 # Template .env
├── backend/
│   ├── app/                     # Code applicatif FastAPI
│   ├── tests/                   # Tests unitaires (39 passing)
│   ├── pyproject.toml           # Dépendances Python (uv)
│   └── Dockerfile
└── frontend/
    ├── src/                     # Code React/TypeScript
    ├── package.json             # Dépendances npm
    ├── vite.config.ts           # Proxy /api → :8000
    └── tailwind.config.ts       # brand.* = CSS variables (3 thèmes)
```

---

## Backend — Arborescence complète

```
backend/app/
├── main.py                      # FastAPI app factory, CORS, lifespan, router mount
├── config.py                    # Settings (pydantic-settings), env_file="../.env" + ".env"
├── dependencies.py              # FastAPI DI factories
├── api/
│   ├── router.py                # Monte tous les sous-routeurs v1
│   └── v1/
│       ├── health.py            # GET /api/v1/
│       ├── chat.py              # POST /chat/, GET /chat/history
│       ├── connections.py       # CRUD + /schema + /annotations
│       ├── dashboards.py        # CRUD dashboards + widgets + refresh + regenerate
│       └── schema.py            # GET /schema/{conn_id} (legacy)
├── core/
│   ├── exceptions.py            # Hiérarchie d'exceptions domaine (incl. DashboardWidgetCreationError)
│   ├── interfaces/
│   │   ├── connector.py         # Protocol AbstractDatabaseConnector (7 méthodes)
│   │   └── llm_provider.py      # Protocol AbstractLLMProvider
│   └── models/
│       ├── annotations.py       # ColumnAnnotation, TableAnnotation, SchemaAnnotations
│       ├── chat.py              # ChatMessage, ChatSession, LLMRequest, LLMResponse, QueryHistoryEntry
│       ├── connection.py        # ConnectionConfig, ConnectionCreate, ConnectionStatus, DBType
│       ├── dashboard.py         # Dashboard, DashboardWidget, WidgetConfig, AddWidgetResponse, ...
│       ├── query.py             # NLQuery, SQLQuery, QueryResult, ColumnMeta, ChatResponse, ChartSuggestion
│       └── schema.py            # SchemaInfo, TableInfo (+ sample_rows), ColumnInfo (+ possible_values, comment), ...
├── connectors/
│   ├── base.py                  # BaseConnector (SQLAlchemy async engine, execute_query, get_table_sample)
│   ├── registry.py              # ConnectorRegistry (scheme → class, connect/disconnect)
│   ├── sqlite.py                # SQLiteConnector (aiosqlite, PRAGMA introspection)
│   └── postgresql.py            # PostgreSQLConnector (asyncpg, information_schema)
├── llm/
│   ├── base.py                  # BaseLLMProvider (LiteLLM, api_base Ollama patch)
│   ├── registry.py              # LLMRegistry (_build_default selon model name)
│   ├── anthropic_provider.py    # Claude models
│   ├── openai_provider.py       # GPT models
│   └── litellm_provider.py      # Fallback générique (Ollama, etc.)
├── services/
│   ├── nl2sql/
│   │   ├── service.py           # NL2SQLService.generate_and_run() — pipeline 10 étapes
│   │   ├── sql_validator.py     # SQLValidator (sqlglot AST, SELECT whitelist, extract_sql, inject_limit)
│   │   ├── prompt_builder.py    # PromptBuilder.build() — system prompt + schema + history
│   │   ├── sql_executor.py      # SQLExecutor.execute() — timeout 30s, LIMIT injection
│   │   └── result_formatter.py  # ResultFormatter.format() + infer_chart() (avec fallback value-based)
│   ├── schema/
│   │   └── service.py           # SchemaService.get_schema() — introspection + sample rows + merge annotations + cache
│   ├── dashboard/
│   │   └── service.py           # DashboardService: create_widget_from_nl, regenerate_widget, execute_widget
│   └── chat/
│       └── service.py           # ChatService — sessions en mémoire (Phase 1)
├── repositories/
│   ├── annotations_repo.py      # AnnotationsRepository — JSON dans .datachat_annotations/{conn_id}.json
│   ├── connection_repo.py       # ConnectionRepository — JSON chiffré dans .datachat_connections/
│   ├── dashboard_repo.py        # DashboardRepository — JSON dans .datachat_dashboards/
│   └── query_repo.py            # QueryRepository — JSONL dans .datachat_history/{conn_id}.jsonl
├── utils/
│   ├── crypto.py                # Fernet encryption (SECRET_KEY → SHA-256)
│   └── logging.py               # structlog JSON
└── vector_store/
    └── memory_store.py          # MemoryVectorStore — cosine similarity in-memory (dev/tests)
```

---

## Modèles Pydantic clés

### `app/core/models/query.py`
```python
class ColumnMeta:
    name: str
    type_name: str
    type_category: "text"|"numeric"|"date"|"boolean"|"json"|"unknown"
    nullable: bool
    inferred: bool = False        # True si type déduit des valeurs (SQLite)

class QueryResult:
    query_id: str
    columns: list[ColumnMeta]
    rows: list[dict[str, Any]]
    total_count: int; truncated: bool; execution_time_ms: int

class ChartSuggestion:
    type: "bar"|"line"|"scatter"|"pie"|"bar_grouped"|"area"
    x_column: str; y_column: str; y_columns: list[str]

class SQLQuery:
    raw_sql: str
    validated_sql: str           # ← toujours utiliser validated_sql
    dialect: str; is_safe: bool; explanation: str
    confidence: float            # 0-1
    validation_warnings: list[str]

class NLQuery:
    text: str; session_id: str; connection_id: str

class ChatResponse:
    message_id: str; session_id: str; nl_query: str
    sql_query: SQLQuery | None; result: QueryResult | None
    chart_suggestion: ChartSuggestion | None
    summary: str; error: str | None; created_at: datetime
```

### `app/core/models/schema.py`
```python
class ColumnInfo:
    name: str; type_name: str; nullable: bool; default: Any
    is_primary_key: bool; is_foreign_key: bool
    comment: str = ""             # Rempli par annotations métier
    possible_values: list[str]    # Valeurs enum (annotations)

class TableInfo:
    name: str; schema_name: str
    columns: list[ColumnInfo]; foreign_keys: list[ForeignKey]; indexes: list[IndexInfo]
    row_count: int | None
    comment: str = ""             # Rempli par annotations métier
    sample_rows: list[dict]       # 3 lignes réelles (fetched at introspection)

    def to_prompt_context(tables=None) -> str   # Format enrichi pour LLM

class SchemaInfo:
    database_name: str; dialect: str; tables: list[TableInfo]
    def get_table(name) -> TableInfo | None
```

### `app/core/models/annotations.py`
```python
class ColumnAnnotation:
    description: str = ""
    possible_values: list[str] = []

class TableAnnotation:
    description: str = ""
    columns: dict[str, ColumnAnnotation] = {}

class SchemaAnnotations:
    conn_id: str
    tables: dict[str, TableAnnotation] = {}
    updated_at: str               # ISO datetime
```

### `app/core/models/dashboard.py`
```python
type WIDGET_TYPES = "chart"|"table"|"kpi"|"text"
type ChartType    = "bar"|"line"|"scatter"|"pie"|"bar_grouped"|"area"

class WidgetConfig:
    chart_type: ChartType | None; x_column: str | None
    y_columns: list[str]; color: str | None; title: str
    inferred: bool = False        # True si config construite par heuristiques

class DashboardWidget:
    id: str; widget_type: WIDGET_TYPES; title: str
    nl_query: str; sql_query: str
    config: WidgetConfig
    position: int; width: 1|2|3; height: 1|2; created_at: datetime

class Dashboard:
    id: str; name: str; description: str; connection_id: str
    widgets: list[DashboardWidget]; created_at: datetime; updated_at: datetime

class AddWidgetRequest:
    nl_text: str; widget_type: WIDGET_TYPES = "chart"

class AddWidgetResponse:
    dashboard: Dashboard; warnings: list[str]

class DashboardCreate:   { name, description, connection_id }
class DashboardUpdate:   { name?, description?, widgets? }
class WidgetRefreshResult: { widget_id, result?, error? }
class DashboardRefreshResult: { dashboard_id, results }
```

### `app/core/models/connection.py`
```python
class DBType = "postgresql"|"mysql"|"sqlite"|"csv"|"mongodb"|"bigquery"
class ConnectionConfig: id, name, db_type, url, schema_name, ssl, created_at, updated_at
class ConnectionCreate:  name, db_type, url, schema_name, ssl
class ConnectionStatus:  conn_id, healthy, latency_ms, error, checked_at
```

---

## API Endpoints

### Connexions
| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/api/v1/connections/` | Liste connexions |
| POST | `/api/v1/connections/` | Créer connexion |
| POST | `/api/v1/connections/{id}/test` | Tester connexion |
| GET | `/api/v1/connections/{id}/schema` | Schéma complet (tables + colonnes) |
| GET | `/api/v1/connections/{id}/annotations` | Annotations métier existantes |
| PUT | `/api/v1/connections/{id}/annotations` | Sauvegarder annotations (invalide cache) |
| DELETE | `/api/v1/connections/{id}` | Supprimer connexion |

### Chat
| Méthode | Route | Description |
|---------|-------|-------------|
| POST | `/api/v1/chat/` | NL query → SQL → résultat |
| GET | `/api/v1/chat/history` | Historique par connexion |

### Dashboards
| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/api/v1/dashboards/` | Liste dashboards |
| POST | `/api/v1/dashboards/` | Créer dashboard |
| GET | `/api/v1/dashboards/{id}` | Détail dashboard |
| PUT | `/api/v1/dashboards/{id}` | Mettre à jour |
| DELETE | `/api/v1/dashboards/{id}` | Supprimer |
| POST | `/api/v1/dashboards/{id}/widgets/from-nl` | Ajouter widget via IA → `AddWidgetResponse` |
| POST | `/api/v1/dashboards/{id}/widgets/{wid}/regenerate` | Regénérer widget (nouveau prompt) |
| DELETE | `/api/v1/dashboards/{id}/widgets/{wid}` | Retirer widget |
| GET | `/api/v1/dashboards/{id}/widgets/{wid}/debug` | Inspecter chaque couche du pipeline |
| POST | `/api/v1/dashboards/{id}/refresh` | Ré-exécuter tous les widgets |

---

## Exceptions domaine (`app/core/exceptions.py`)

```
DBIAError
├── ConnectionError
│   ├── ConnectionNotFoundError
│   ├── ConnectionFailedError
│   └── ConnectorNotFoundError / UnsupportedDatabaseError
├── SQLError
│   ├── SQLValidationError; SQLSecurityError; SQLExtractionError; SQLExecutionError
├── LLMError
│   ├── LLMProviderNotFoundError; LLMGenerationError
├── SchemaError
│   └── SchemaNotFoundError
├── DashboardNotFoundError
├── DashboardWidgetCreationError
└── AuditError → AuditTimeoutError
```

---

## Config (`app/config.py`)

```python
litellm_default_model: str = "claude-sonnet-4-6"
litellm_summary_model: str = "claude-haiku-4-5-20251001"
ollama_api_base: str = "http://localhost:11434"
qdrant_url: str = "http://localhost:6333"
redis_url: str = "redis://localhost:6379/0"
database_url: str = "sqlite+aiosqlite:///./datachat.db"
secret_key: str = "dev-secret-key-change-in-production"
schema_rag_min_tables: int = 20
max_query_rows: int = 1000
query_timeout_seconds: int = 30
debug: bool = False               # True → structlog ConsoleRenderer + verbose logs
```

---

## Pipeline NL2SQL — `NL2SQLService.generate_and_run()`

```
Entrée: NLQuery + connector + schema_info + history

1. Prompt build     → PromptBuilder.build() — inclut sample_rows + annotations dans schema context
2. LLM complete     → llm.complete(LLMRequest) → LLMResponse
3. SQL extract      → SQLValidator.extract_sql()   # tags <sql> / ```sql / raw SELECT
4. AST validate     → SQLValidator.validate(sql, dialect, schema_info)
5. Safety gate      → SELECT whitelist, system tables blocklist, func blocklist
6. Table validate   → toutes les tables/colonnes existent dans schema_info
7. LIMIT inject     → SQLValidator.inject_limit(sql, max_rows)
8. Execute          → SQLExecutor.execute(validated_sql, connector)  # timeout 30s
9. Format           → ResultFormatter.format(result) + infer_chart(result)
                      (type inference value-based pour SQLite qui retourne "unknown")
10. Summarize       → llm.complete(summary_prompt, model=summary_model)

Sortie: ChatResponse
```

**Logs structlog disponibles (DEBUG=true) :**
- `prompt_built`, `prompt_system`, `prompt_user`
- `llm_request_sent`, `llm_raw_response`
- `sql_extracted`, `sql_parse_ok`, `sql_whitelist_ok`, `sql_system_tables_ok`, `sql_functions_ok`, `sql_schema_refs_ok`, `sql_transpiled`
- `sql_limit_injected`, `sql_executing`, `sql_validated`
- `chart_suggestion`

---

## Pipeline Schéma enrichi — `SchemaService.get_schema()`

```
1. connector.introspect_schema()      → SchemaInfo brut
2. Pour chaque table:
   connector.get_table_sample(name, 3) → table.sample_rows (3 lignes réelles)
3. AnnotationsRepository.get(conn_id) → merge dans table.comment, col.comment, col.possible_values
4. Cache en mémoire (classe-level dict)

Invalider cache : SchemaService.invalidate(conn_id)  ← appelé sur PUT /annotations
```

**Format prompt_context enrichi :**
```
Table: commandes (~4 rows) -- Commandes passées par les clients
  Columns:
    id (INTEGER PK)
    montant (REAL) -- Montant en euros
    statut (TEXT) -- Valeurs: 'expédiée', 'validée', 'en_attente'
  FK: client_id → clients.id
  Sample data:
    id=1  client_id=1  montant=450.0  statut='expédiée'
```

---

## Patterns à suivre

### Nouveau Repository
```python
class XxxRepository:
    def __init__(self, settings: "Settings"):
        self._store_dir = Path(".datachat_xxx")
        self._store_dir.mkdir(exist_ok=True)

    def _path(self, id: str) -> Path:
        return self._store_dir / f"{id}.json"

    async def save(self, obj: Xxx) -> Xxx: ...
    async def get(self, id: str) -> Xxx | None: ...
    async def list_all(self) -> list[Xxx]: ...
    async def delete(self, id: str) -> bool: ...
```

### Nouvelle Route FastAPI
```python
@router.post("/", response_model=Xxx, status_code=201)
async def create_item(data: XxxCreate, settings: Annotated[Settings, Depends(get_settings)]):
    repo = XxxRepository(settings)
    obj = Xxx(id=str(uuid.uuid4()), **data.model_dump())
    return await repo.save(obj)
```

---

## Frontend — Arborescence complète

```
frontend/src/
├── App.tsx                      # BrowserRouter + routes + apply data-theme attribute
├── main.tsx                     # ReactDOM.createRoot, QueryClientProvider
├── index.css                    # Tailwind + CSS vars thèmes + .btn-primary, .input-field, .card
├── api/
│   ├── client.ts                # Axios instance, baseURL /api/v1, timeout 60s
│   ├── types.ts                 # Miroirs TypeScript des modèles Pydantic
│   ├── chat.ts                  # chatApi.send(), chatApi.history()
│   ├── connections.ts           # connectionsApi.list/create/test/delete/getSchema/getAnnotations/saveAnnotations()
│   └── dashboards.ts            # dashboardsApi: list/create/get/update/delete/addWidgetFromNL/regenerateWidget/removeWidget/refresh()
├── stores/
│   ├── chatStore.ts             # Zustand: sessions, isLoading, messages
│   ├── connectionStore.ts       # Zustand + persist: connections[], activeConnectionId
│   ├── dashboardStore.ts        # Zustand: widgetResults, widgetLoading, setWidgetResult/Loading
│   └── themeStore.ts            # Zustand + persist: theme ('cyan'|'violet'|'amber'), setTheme()
├── pages/
│   ├── ChatPage.tsx             # Chat NL→SQL, session par connexion
│   ├── ConnectionsPage.tsx      # CRUD connexions, bouton "Annoter le schéma" → /annotate
│   ├── ConnectionAnnotationsPage.tsx  # Wizard: descriptions + valeurs possibles par table/colonne
│   ├── DashboardsPage.tsx       # Liste dashboards avec création inline
│   ├── DashboardViewPage.tsx    # Vue lecture seule + refresh
│   └── DashboardBuilderPage.tsx # Édition: ajout widget, move, resize, delete, regenerate
└── components/
    ├── shared/
    │   ├── Layout.tsx           # Flexbox app shell: Sidebar + <Outlet>
    │   └── Sidebar.tsx          # Logo, connection selector, nav links, sélecteur 3 thèmes
    ├── chat/
    │   ├── ChatWindow.tsx; MessageBubble.tsx; QueryInput.tsx; SQLPreview.tsx; ResultTable.tsx
    └── dashboard/
        ├── ChartWidget.tsx      # Recharts: bar/line/area/pie/scatter (xKey/yKey fallback value-based)
        ├── TableWidget.tsx      # Wrapper ResultTable
        ├── KPIWidget.tsx        # Chiffre unique centré
        ├── Widget.tsx           # Shell + pencil edit inline (nl_query éditable + Regénérer)
        ├── DashboardGrid.tsx    # CSS Grid 12 col, passe onRegenerate
        └── AddWidgetPanel.tsx   # AI textarea + type selector + warnings
```

---

## Types TypeScript (`src/api/types.ts`)

```typescript
// Connexions
type DBType = 'postgresql'|'mysql'|'sqlite'|'csv'|'mongodb'|'bigquery'
interface ConnectionConfig  { id, name, db_type, url, schema_name, ssl, created_at, updated_at }
interface ConnectionCreate  { name, db_type, url, schema_name?, ssl? }
interface ConnectionStatus  { conn_id, healthy, latency_ms, error, checked_at }

// Requêtes
interface ColumnMeta        { name, type_name, type_category, nullable, inferred? }
interface QueryResult       { query_id, columns, rows, total_count, truncated, execution_time_ms }
interface ChartSuggestion   { type, x_column, y_column, y_columns }
interface SQLQuery           { raw_sql, validated_sql, dialect, is_safe, explanation, confidence, validation_warnings }
interface ChatResponse       { message_id, session_id, nl_query, sql_query?, result?, chart_suggestion?, summary, error?, created_at }

// Schéma
interface SchemaColumn      { name, type_name, nullable, is_primary_key, is_foreign_key, comment, possible_values }
interface SchemaTable       { name, schema_name, columns, row_count }
interface SchemaInfo        { database_name, dialect, tables }

// Annotations
interface ColumnAnnotation  { description, possible_values }
interface TableAnnotation   { description, columns: Record<string, ColumnAnnotation> }
interface SchemaAnnotations { conn_id, tables: Record<string, TableAnnotation>, updated_at }

// Dashboards
type WidgetType = 'chart'|'table'|'kpi'|'text'
type ChartType  = 'bar'|'line'|'scatter'|'pie'|'bar_grouped'|'area'
interface WidgetConfig      { chart_type, x_column, y_columns, color, title, inferred? }
interface DashboardWidget   { id, widget_type, title, nl_query, sql_query, config, position, width, height, created_at }
interface Dashboard         { id, name, description, connection_id, widgets, created_at, updated_at }
interface DashboardCreate   { name, description?, connection_id }
interface DashboardUpdate   { name?, description?, widgets? }
interface AddWidgetRequest  { nl_text, widget_type? }
interface AddWidgetResponse { dashboard, warnings }
interface RegenerateWidgetRequest { nl_text }
interface WidgetRefreshResult     { widget_id, result?, error? }
interface DashboardRefreshResult  { dashboard_id, results }
```

---

## Design System Frontend — Thèmes

Brand colors = CSS variables (3 thèmes via `data-theme` sur `<html>`) :

| Token Tailwind | Variable CSS | Cyan | Violet | Ambre |
|----------------|-------------|------|--------|-------|
| `brand-400` | `--brand-400` | #38bdf8 | #c084fc | #fbbf24 |
| `brand-500` | `--brand-500` | #0ea5e9 | #a855f7 | #f59e0b |
| `brand-600` | `--brand-600` | #0284c7 | #9333ea | #d97706 |
| `brand-700` | `--brand-700` | #0369a1 | #7e22ce | #b45309 |

Sélecteur de thème dans `Sidebar.tsx` — 3 boutons ronds, persisté dans `themeStore` (localStorage).

| Token | Usage |
|-------|-------|
| `bg-gray-950` | Background principal |
| `bg-gray-900` | Cards, panels |
| `bg-gray-800` | Borders, inputs |
| `.card` | gray-900 bg + gray-800 border + rounded-xl + p-4 |
| `.btn-primary` | brand-600 bg + white text |
| `.btn-ghost` | transparent + gray-400 text |
| `.input-field` | gray-900 bg + gray-700 border + brand-500 focus |

---

## Routes frontend (`App.tsx`)

```
/                        → redirect /chat
/chat                    → ChatPage
/connections             → ConnectionsPage
/connections/:connId/annotate → ConnectionAnnotationsPage
/dashboards              → DashboardsPage
/dashboards/:id          → DashboardViewPage
/dashboards/:id/edit     → DashboardBuilderPage
```

---

## Commandes de développement

```bash
make infra           # docker-compose up redis qdrant
make backend         # cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000
make frontend        # cd frontend && npm run dev  → :5173
make test-unit       # cd backend && VIRTUAL_ENV="" .venv/bin/pytest tests/unit -v
make demo-db         # Créer backend/demo.db (3 clients, 4 commandes)
```

**Vérification rapide :**
```bash
cd backend && VIRTUAL_ENV="" .venv/bin/pytest tests/unit -q   # 39 passed
cd frontend && npm run build                                   # 0 erreurs TS
```

---

## État d'avancement

| Fonctionnalité | Statut |
|----------------|--------|
| Phase 1 — MVP NL2SQL (PostgreSQL + SQLite + Claude) | ✅ Complet — 39/39 tests |
| Debug logging structlog (prompt in/out, SQL, validations) | ✅ Complet |
| Chart inference robuste (fallback value-based SQLite) | ✅ Complet |
| Warnings widget inferred + AddWidgetResponse | ✅ Complet |
| Dashboard CRUD + widgets + refresh | ✅ Complet |
| **Thèmes** (cyan/violet/ambre, CSS vars, persisté) | ✅ Complet |
| **Sample data** dans schéma LLM (3 lignes réelles/table) | ✅ Complet |
| **Annotations métier** (descriptions + enums par table/colonne) | ✅ Complet |
| **Widget regénérable** (nl_query visible + crayon + Regénérer) | ✅ Complet |
| Phase 2 — Streaming WebSocket | 🔲 À faire |
| Phase 2 — MySQL/CSV connecteurs | 🔲 À faire |
| Phase 3 — Schema Explorer + Audit | 🔲 À faire |
| Phase 4 — Auth + Production | 🔲 À faire |

---

## Règles de sécurité non-négociables

1. **Jamais `raw_sql`** — toujours `validated_sql` avant exécution
2. **SQLValidator obligatoire** sur tout SQL venant du LLM
3. **SELECT uniquement** — INSERT/UPDATE/DELETE/DROP bloqués au niveau AST
4. **Timeout 30s** — hardcodé, non configurable via UI
5. **Frontière API** — zéro logique métier dans les route handlers
6. **`app/core/`** — zéro import externe (Protocols + Pydantic uniquement)
