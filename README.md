# DataChat — Natural Language Interface for Databases

> Ask questions in plain language. Get SQL, results, and visualizations — powered by any LLM, connected to any database.

![License](https://img.shields.io/badge/license-MIT-blue) ![Python](https://img.shields.io/badge/python-3.11+-green) ![React](https://img.shields.io/badge/react-18-61DAFB)

---

## What it does

DataChat lets you query, explore, and visualize any database without writing SQL.

- **Chat with your data** — type a question in French or English, get a validated SQL query and formatted results
- **Build dashboards** — describe visualizations in natural language, the AI generates and arranges them for you
- **Source-agnostic** — swap databases by changing a URL, swap LLMs by changing one config line
- **Safe by design** — all generated SQL goes through an AST-level validator before execution (no regex, no tricks)

---

## Screenshots

| Chat | Dashboard |
|------|-----------|
| ![Chat](.github/chat.png) | ![Dashboard](.github/dashboard.png) |

---

## Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI + Pydantic v2 |
| LLM | LiteLLM (Claude, OpenAI, Ollama, 100+ providers) |
| SQL Validation | sqlglot (AST-based) |
| Databases | SQLAlchemy 2.x async |
| Schema RAG | Qdrant vector store |
| Async jobs | Celery + Redis |
| Frontend | React 18 + Vite + TypeScript |
| State | Zustand + React Query |
| Charts | Recharts |
| Style | Tailwind CSS |

---

## Quick start

### Prerequisites

- Python 3.11+, [uv](https://github.com/astral-sh/uv)
- Node.js 18+
- Docker (for Redis + Qdrant)
- An LLM — [Ollama](https://ollama.com) (free, local) or an API key

### 1. Clone & install

```bash
git clone https://github.com/your-username/db-ia.git
cd db-ia
make install
```

### 2. Configure environment

Copy `.env.example` to `.env` and fill in:

```bash
cp .env.example .env
```

**With Ollama (free, no API key needed):**
```bash
# Pull the model first
ollama pull llama3.2

# In .env:
LITELLM_DEFAULT_MODEL=ollama/llama3.2
LITELLM_SUMMARY_MODEL=ollama/llama3.2
ANTHROPIC_API_KEY=dummy
SECRET_KEY=your-random-secret-key
```

**With Claude (Anthropic):**
```bash
ANTHROPIC_API_KEY=sk-ant-...
LITELLM_DEFAULT_MODEL=claude-sonnet-4-6
SECRET_KEY=your-random-secret-key
```

### 3. Start services

```bash
# Terminal 1 — Redis + Qdrant
make infra

# Terminal 2 — Backend API
make backend

# Terminal 3 — Frontend
make frontend
```

Open **http://localhost:5173**

### 4. Try it

1. Go to **Connexions** → add a connection
   - Name: `demo`
   - URL: `sqlite:///./demo.db`
2. Run `make demo-db` to create a sample SQLite database
3. Go to **Chat** → select `demo` → ask: *"How many customers are there?"*
4. Go to **Dashboards** → create a dashboard → describe a visualization

---

## Architecture

```
React (Vite + TypeScript + Tailwind)
  ↕ REST
FastAPI + Pydantic v2
  ↕
NL2SQL Pipeline (10 steps) ←→ LiteLLM (Claude / OpenAI / Ollama)
  ↕                               ↕
SQLAlchemy async             Qdrant (schema RAG)
  ↕
PostgreSQL │ MySQL │ SQLite │ CSV │ MongoDB │ BigQuery
```

### NL → SQL pipeline (10 steps)

Every natural language query passes through these steps in order. A failure at any step returns an error — execution is never reached.

```
1. Schema RAG     → find relevant tables via vector similarity (Qdrant)
2. Prompt build   → assemble schema + history + safety rules
3. LLM generate   → produce SQL + explanation
4. SQL extract    → isolate SQL block from LLM response
5. AST parse      → sqlglot parse — hard stop on invalid syntax
6. Safety gate    → SELECT whitelist, block system tables & dangerous functions
7. Table validate → verify all referenced tables/columns exist in schema
8. Complexity     → inject LIMIT if missing (max 1000 rows)
9. Execute        → run via connector, 30s timeout, READ ONLY transaction
10. Format        → structured result + chart suggestion + NL summary
```

### Security model

| Threat | Mitigation |
|--------|-----------|
| SQL injection via LLM | sqlglot AST validation — obfuscation tricks don't fool a parser |
| Destructive queries | Only `SELECT` allowed — `INSERT/UPDATE/DELETE/DROP` blocked at AST level |
| System table access | Blocklist: `information_schema`, `pg_catalog`, `mysql.*`, `sqlite_*` |
| Runaway queries | 30s timeout (hardcoded), LIMIT 1000 enforced |
| Credential exposure | Fernet encryption at rest, SELECT-only DB user recommended |

---

## Adding a database connector

1. Create `backend/app/connectors/your_db.py`
2. Implement `AbstractDatabaseConnector` from `app/core/interfaces/connector.py`
3. Register in `backend/app/connectors/registry.py`:
   ```python
   CONNECTOR_REGISTRY["yourdb"] = YourDBConnector
   ```
4. Add connection form fields in `frontend/src/pages/ConnectionsPage.tsx`

See `docs/guides/add-db-connector.md` for the full guide.

## Adding an LLM provider

1. Create `backend/app/llm/your_provider.py` extending `BaseLLMProvider`
2. Register in `backend/app/llm/registry.py`
3. Set `LITELLM_DEFAULT_MODEL=your-provider/model-name` in `.env`

Most providers supported by LiteLLM work with zero code changes.

---

## Development

```bash
make help           # List all commands

make infra          # Start Redis + Qdrant
make backend        # Start FastAPI on :8000
make frontend       # Start Vite on :5173
make worker         # Start Celery worker

make test           # Run all tests
make test-unit      # Run unit tests only (no infra required)
make test-cov       # Tests with coverage report

make demo-db        # Create demo SQLite database
make clean          # Remove build artifacts
```

---

## Project structure

```
db-ia/
├── backend/
│   └── app/
│       ├── api/v1/          # REST endpoints (thin layer, zero business logic)
│       ├── core/            # Domain models + interfaces (zero external deps)
│       ├── connectors/      # Database connectors (SQLite, PostgreSQL, ...)
│       ├── llm/             # LLM providers (Anthropic, OpenAI, Ollama, ...)
│       ├── services/        # Business logic (NL2SQL, Schema, Dashboard, ...)
│       └── repositories/    # File-based storage (Phase 1)
├── frontend/
│   └── src/
│       ├── pages/           # ChatPage, DashboardsPage, ConnectionsPage, ...
│       ├── components/      # chat/, dashboard/, shared/
│       ├── stores/          # Zustand stores
│       └── api/             # Typed API client
└── docs/                    # Architecture, guides, ADRs
```

---

## Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| **1 — MVP NL2SQL** | ✅ Done | Full pipeline, SQLite + PostgreSQL, Claude, Chat UI |
| **1 — Dashboards** | ✅ Done | AI-assisted dashboard builder, charts + tables + KPIs |
| **2 — Breadth** | 🔲 Next | MySQL/CSV, WebSocket streaming, query history UI, export |
| **3 — Explorer + Audit** | 🔲 Planned | Schema explorer, 4 auditors, Celery async jobs |
| **4 — Production** | 🔲 Planned | Auth JWT, BigQuery/MongoDB, encryption, Docker/K8s |

---

## License

MIT
