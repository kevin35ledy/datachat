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
    └── tailwind.config.ts       # Thème (brand cyan, gray-950)
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
│       ├── connections.py       # CRUD /connections/
│       └── schema.py            # GET /schema/{conn_id}
├── core/
│   ├── exceptions.py            # Hiérarchie d'exceptions domaine
│   ├── interfaces/
│   │   ├── connector.py         # Protocol AbstractDatabaseConnector (7 méthodes)
│   │   └── llm_provider.py      # Protocol AbstractLLMProvider
│   └── models/
│       ├── chat.py              # ChatMessage, ChatSession, LLMRequest, LLMResponse, QueryHistoryEntry
│       ├── connection.py        # ConnectionConfig, ConnectionCreate, ConnectionStatus, DBType
│       ├── query.py             # NLQuery, SQLQuery, QueryResult, ColumnMeta, ChatResponse, ChartSuggestion
│       └── schema.py            # SchemaInfo, TableInfo, ColumnInfo, ForeignKey, IndexInfo
├── connectors/
│   ├── base.py                  # BaseConnector (SQLAlchemy async engine, execute_query, get_table_sample)
│   ├── registry.py              # ConnectorRegistry (scheme → class)
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
│   │   └── result_formatter.py  # ResultFormatter.format() + infer_chart()
│   ├── schema/
│   │   └── service.py           # SchemaService.get_schema() — introspection + cache classe
│   └── chat/
│       └── service.py           # ChatService — sessions en mémoire (Phase 1)
├── repositories/
│   ├── connection_repo.py       # ConnectionRepository — JSON chiffré dans .datachat_connections/
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

class QueryResult:
    query_id: str
    columns: list[ColumnMeta]
    rows: list[dict[str, Any]]
    total_count: int
    truncated: bool
    execution_time_ms: int

class ChartSuggestion:
    type: "bar"|"line"|"scatter"|"pie"|"bar_grouped"|"area"
    x_column: str
    y_column: str
    y_columns: list[str]

class SQLQuery:
    raw_sql: str
    validated_sql: str           # ← toujours utiliser validated_sql
    dialect: str
    is_safe: bool
    explanation: str
    confidence: float            # 0-1
    validation_warnings: list[str]

class NLQuery:
    text: str
    session_id: str
    connection_id: str

class ChatResponse:
    message_id: str
    session_id: str
    nl_query: str
    sql_query: SQLQuery | None
    result: QueryResult | None
    chart_suggestion: ChartSuggestion | None
    summary: str
    error: str | None
    created_at: datetime
```

### `app/core/models/connection.py`
```python
class DBType = "postgresql"|"mysql"|"sqlite"|"csv"|"mongodb"|"bigquery"

class ConnectionConfig:
    id: str; name: str; db_type: DBType; url: str
    schema_name: str; ssl: bool; created_at: datetime; updated_at: datetime

class ConnectionCreate:
    name: str; db_type: DBType; url: str; schema_name: str; ssl: bool

class ConnectionStatus:
    conn_id: str; healthy: bool; latency_ms: int|None; error: str|None; checked_at: datetime
```

### `app/core/models/chat.py`
```python
class LLMRequest:
    messages: list[dict[str, str]]
    temperature: float = 0.1
    max_tokens: int = 1500
    model_override: str | None

class LLMResponse:
    content: str; model: str
    input_tokens: int; output_tokens: int; latency_ms: int

class QueryHistoryEntry:
    id: str; connection_id: str; session_id: str
    nl_text: str; sql_text: str; row_count: int; execution_time_ms: int; created_at: datetime
```

### `app/core/models/schema.py`
```python
class SchemaInfo:
    database_name: str; dialect: str; tables: list[TableInfo]
    def to_prompt_context(tables: list[str] | None) -> str   # → text pour LLM

class TableInfo:
    name: str; schema_name: str; columns: list[ColumnInfo]
    foreign_keys: list[ForeignKey]; indexes: list[IndexInfo]; row_count: int|None
```

---

## API Endpoints

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/api/v1/` | Health check |
| GET | `/api/v1/connections/` | Liste connexions |
| POST | `/api/v1/connections/` | Créer connexion |
| POST | `/api/v1/connections/{id}/test` | Tester connexion |
| DELETE | `/api/v1/connections/{id}` | Supprimer connexion |
| POST | `/api/v1/chat/` | NL query → SQL → résultat |
| GET | `/api/v1/chat/history` | Historique par connexion |
| GET | `/api/v1/schema/{conn_id}` | Schéma DB (avec cache) |

**À ajouter (Dashboard feature) :**

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/api/v1/dashboards/` | Liste dashboards |
| POST | `/api/v1/dashboards/` | Créer dashboard |
| GET | `/api/v1/dashboards/{id}` | Détail dashboard |
| PUT | `/api/v1/dashboards/{id}` | Mettre à jour |
| DELETE | `/api/v1/dashboards/{id}` | Supprimer |
| POST | `/api/v1/dashboards/{id}/widgets/from-nl` | Ajouter widget via IA |
| DELETE | `/api/v1/dashboards/{id}/widgets/{wid}` | Retirer widget |
| POST | `/api/v1/dashboards/{id}/refresh` | Ré-exécuter tous les widgets |

---

## Exceptions domaine (`app/core/exceptions.py`)

```
DBIAError
├── ConnectionError
│   ├── ConnectionNotFoundError
│   ├── ConnectionFailedError
│   └── ConnectorNotFoundError
├── SQLError
│   ├── SQLValidationError
│   ├── SQLSecurityError
│   ├── SQLExtractionError
│   └── SQLExecutionError
├── LLMError
│   ├── LLMProviderNotFoundError
│   └── LLMGenerationError
├── SchemaError
│   └── SchemaNotFoundError
└── AuditError
    └── AuditTimeoutError
```
**À ajouter :** `DashboardWidgetCreationError(DBIAError)`

---

## Config (`app/config.py`)

```python
# LLM
litellm_default_model: str = "claude-sonnet-4-6"   # override .env: ollama/llama3.2
litellm_summary_model: str = "claude-haiku-4-5-20251001"
ollama_api_base: str = "http://localhost:11434"

# Infrastructure
qdrant_url: str = "http://localhost:6333"
redis_url: str = "redis://localhost:6379/0"
database_url: str = "sqlite+aiosqlite:///./datachat.db"

# Sécurité
secret_key: str = "dev-secret-key-change-in-production"
schema_rag_min_tables: int = 20   # En-dessous → RAG contourné

# Limites
max_query_rows: int = 1000
query_timeout_seconds: int = 30
```

env_file recherche `../. env` puis `.env` (CWD = `backend/` au runtime).

---

## Pipeline NL2SQL — `NL2SQLService.generate_and_run()`

```
Entrée: NLQuery + connector + schema_info + history

1. Prompt build     → PromptBuilder.build(nl_query, schema_info, relevant_tables, history, dialect)
2. LLM complete     → llm.complete(LLMRequest) → LLMResponse
3. SQL extract      → SQLValidator.extract_sql(response.content)   # tags <sql> / ```sql / raw SELECT
4. AST validate     → SQLValidator.validate(sql, dialect, schema_info)
5. Safety gate      → SELECT whitelist, system tables blocklist, func blocklist
6. Table validate   → toutes les tables/colonnes existent dans schema_info
7. LIMIT inject     → SQLValidator.inject_limit(sql, max_rows)
8. Execute          → SQLExecutor.execute(validated_sql, connector)  # timeout 30s
9. Format           → ResultFormatter.format(result) + infer_chart(result)
10. Summarize       → llm.complete(summary_prompt, model=summary_model)

Sortie: ChatResponse
```

**Sécurité non-négociable :** validated_sql uniquement, jamais raw_sql.

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

    async def save(self, obj: Xxx) -> Xxx:
        obj.updated_at = datetime.utcnow()
        self._path(obj.id).write_text(obj.model_dump_json())
        return obj

    async def get(self, id: str) -> Xxx | None:
        p = self._path(id)
        if not p.exists(): return None
        return Xxx.model_validate_json(p.read_text())

    async def list_all(self) -> list[Xxx]:
        items = [Xxx.model_validate_json(p.read_text()) for p in self._store_dir.glob("*.json")]
        return sorted(items, key=lambda x: x.created_at)

    async def delete(self, id: str) -> bool:
        p = self._path(id)
        if not p.exists(): return False
        p.unlink(); return True
```

### Nouvelle Route FastAPI
```python
router = APIRouter()

@router.get("/", response_model=list[Xxx])
async def list_items(settings: Annotated[Settings, Depends(get_settings)]) -> list[Xxx]:
    repo = XxxRepository(settings)
    return await repo.list_all()

@router.post("/", response_model=Xxx, status_code=201)
async def create_item(data: XxxCreate, settings: Annotated[Settings, Depends(get_settings)]):
    repo = XxxRepository(settings)
    obj = Xxx(id=str(uuid.uuid4()), **data.model_dump(), created_at=now, updated_at=now)
    return await repo.save(obj)
```

---

## Frontend — Arborescence complète

```
frontend/src/
├── App.tsx                      # BrowserRouter, routes: /chat, /connections (+ /dashboards à venir)
├── main.tsx                     # ReactDOM.createRoot, QueryClientProvider, RouterProvider
├── index.css                    # Tailwind + .btn-primary, .btn-ghost, .input-field, .card
├── api/
│   ├── client.ts                # Axios instance, baseURL /api/v1, timeout 60s, error interceptor
│   ├── types.ts                 # Miroirs TypeScript des modèles Pydantic
│   ├── chat.ts                  # chatApi.send(), chatApi.history()
│   └── connections.ts           # connectionsApi.list/create/test/delete()
├── stores/
│   ├── chatStore.ts             # Zustand: sessions, isLoading, addUserMessage, addAssistantMessage
│   └── connectionStore.ts       # Zustand + localStorage persist: connections[], activeConnectionId
├── pages/
│   ├── ChatPage.tsx             # Chat NL→SQL, session par connexion
│   └── ConnectionsPage.tsx      # CRUD connexions avec test inline
└── components/
    ├── shared/
    │   ├── Layout.tsx           # Flexbox app shell: Sidebar + <Outlet>
    │   └── Sidebar.tsx          # Logo, connection selector, nav links (Chat, Connexions)
    └── chat/
        ├── ChatWindow.tsx       # Container scrollable, auto-scroll, spinner
        ├── MessageBubble.tsx    # User (droite, brand) / Assistant (gauche, dark)
        ├── QueryInput.tsx       # Textarea auto-grow, Enter=envoyer, Shift+Enter=newline
        ├── SQLPreview.tsx       # Collapsible, execution time, confidence badge, copy
        └── ResultTable.tsx      # Tableau paginé (20/page), CSV export, null handling
```

**À créer (Dashboard feature) :**
```
src/
├── api/dashboards.ts
├── stores/dashboardStore.ts
├── pages/
│   ├── DashboardsPage.tsx
│   ├── DashboardViewPage.tsx
│   └── DashboardBuilderPage.tsx
└── components/dashboard/
    ├── ChartWidget.tsx          # Recharts: bar/line/area/pie/scatter
    ├── TableWidget.tsx          # Wrapper ResultTable
    ├── KPIWidget.tsx            # Chiffre unique centré
    ├── Widget.tsx               # Shell: header + loading/error/content
    ├── DashboardGrid.tsx        # CSS Grid 12 col
    └── AddWidgetPanel.tsx       # AI textarea + type selector
```

---

## Types TypeScript existants (`src/api/types.ts`)

```typescript
type DBType = 'postgresql'|'mysql'|'sqlite'|'csv'|'mongodb'|'bigquery'

interface ConnectionConfig { id, name, db_type, url, schema_name, ssl, created_at, updated_at }
interface ConnectionCreate  { name, db_type, url, schema_name?, ssl? }
interface ConnectionStatus  { conn_id, healthy, latency_ms, error, checked_at }

interface ColumnMeta        { name, type_name, type_category, nullable }
interface QueryResult       { query_id, columns, rows, total_count, truncated, execution_time_ms }
interface ChartSuggestion   { type, x_column, y_column, y_columns }
interface SQLQuery           { raw_sql, validated_sql, dialect, is_safe, explanation, confidence, validation_warnings }
interface ChatResponse       { message_id, session_id, nl_query, sql_query?, result?, chart_suggestion?, summary, error?, created_at }
interface QueryHistoryEntry  { id, connection_id, session_id, nl_text, sql_text, row_count, execution_time_ms, created_at }
interface SchemaInfo         { database_name, dialect, tables }
```

---

## Design System Frontend

| Token | Valeur | Usage |
|-------|--------|-------|
| `bg-gray-950` | `#030712` | Background principal |
| `bg-gray-900` | `#111827` | Cards, panels |
| `bg-gray-800` | `#1f2937` | Borders, inputs |
| `brand-500` | `#06b6d4` | Accents, focus rings |
| `brand-600` | `#0891b2` | Boutons primaires |
| `.card` | gray-900 bg + gray-800 border + rounded-xl + p-4 | Conteneurs |
| `.btn-primary` | brand-600 bg + white text | Actions principales |
| `.btn-ghost` | transparent + gray-400 text | Actions secondaires |
| `.input-field` | gray-900 bg + gray-700 border + brand-500 focus | Formulaires |

**Couleurs graphiques :** `['#06b6d4', '#0ea5e9', '#6366f1', '#a855f7', '#ec4899']`

**Police code :** JetBrains Mono (CSS var `--font-mono`)

---

## Dépendances clés

### Backend (pyproject.toml)
| Package | Usage |
|---------|-------|
| `fastapi ≥0.111` | API framework |
| `sqlalchemy[asyncio] 2.x` | ORM async |
| `aiosqlite` | SQLite async |
| `asyncpg` | PostgreSQL async |
| `litellm ≥1.40` | Interface LLM unifiée |
| `sqlglot ≥23` | Parsing SQL AST |
| `qdrant-client` | Vector store |
| `pydantic-settings` | Config via .env |
| `cryptography` | Fernet encryption |
| `structlog` | JSON logging |
| `celery` | Async jobs (Phase 3) |

### Frontend (package.json)
| Package | Usage |
|---------|-------|
| `react 18` + `react-dom` | UI framework |
| `react-router-dom 6` | Routing |
| `@tanstack/react-query 5` | Server state, cache |
| `zustand 4` | Client state |
| `axios` | HTTP client |
| `recharts 2.12` | **Graphiques — installé, pas encore utilisé** |
| `react-syntax-highlighter` | Coloration SQL |
| `lucide-react` | Icônes |
| `clsx` + `tailwind-merge` | Classnames |

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
cd backend && VIRTUAL_ENV="" .venv/bin/python -c "from app.main import app; print(app.title)"
cd frontend && npm run build
```

---

## État d'avancement

| Phase | Statut |
|-------|--------|
| Phase 1 — MVP NL2SQL | ✅ Complet — 39/39 tests |
| Dashboard — Backend models + API | ✅ Complet |
| Dashboard — Frontend pages + composants | ✅ Complet |
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
