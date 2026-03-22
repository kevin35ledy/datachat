.PHONY: help infra infra-down backend frontend dev test test-unit install clean

help:  ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Infrastructure ───────────────────────────────────────────────────────────

infra:  ## Start Redis + Qdrant (required for backend)
	docker-compose up -d redis qdrant
	@echo "Waiting for services..."
	@sleep 3
	@echo "Redis and Qdrant are up."

infra-down:  ## Stop infrastructure services
	docker-compose down

# ── Backend ──────────────────────────────────────────────────────────────────

install-backend:  ## Install backend Python dependencies (requires uv)
	cd backend && uv sync

backend:  ## Start the FastAPI backend (requires infra running)
	cd backend && VIRTUAL_ENV="" .venv/bin/uvicorn app.main:app --reload --port 8000

worker:  ## Start Celery worker
	cd backend && VIRTUAL_ENV="" .venv/bin/celery -A app.workers.celery_app worker --loglevel=info

# ── Frontend ─────────────────────────────────────────────────────────────────

install-frontend:  ## Install frontend npm dependencies
	cd frontend && npm install

frontend:  ## Start the Vite dev server
	cd frontend && npm run dev

build-frontend:  ## Build frontend for production
	cd frontend && npm run build

# ── Development ──────────────────────────────────────────────────────────────

install:  ## Install all dependencies
	$(MAKE) install-backend install-frontend

dev:  ## Start everything for local development (in separate terminals)
	@echo "Run in separate terminals:"
	@echo "  make infra"
	@echo "  make backend"
	@echo "  make frontend"

# ── Tests ────────────────────────────────────────────────────────────────────

test:  ## Run all backend tests
	cd backend && VIRTUAL_ENV="" .venv/bin/pytest -v

test-unit:  ## Run unit tests only (no external services required)
	cd backend && VIRTUAL_ENV="" .venv/bin/pytest tests/unit -v

test-cov:  ## Run tests with coverage report
	cd backend && VIRTUAL_ENV="" .venv/bin/pytest --cov=app --cov-report=html --cov-report=term-missing

# ── Utilities ────────────────────────────────────────────────────────────────

demo-db:  ## Create a demo SQLite database for testing
	cd backend && python -c "\
import sqlite3; \
conn = sqlite3.connect('demo.db'); \
conn.executescript('''\
CREATE TABLE IF NOT EXISTS clients (id INTEGER PRIMARY KEY, nom TEXT, email TEXT, ville TEXT, ca_total REAL DEFAULT 0);\
CREATE TABLE IF NOT EXISTS commandes (id INTEGER PRIMARY KEY, client_id INTEGER REFERENCES clients(id), montant REAL, statut TEXT);\
INSERT OR IGNORE INTO clients VALUES (1, 'Alice Martin', 'alice@example.com', 'Paris', 5420.50);\
INSERT OR IGNORE INTO clients VALUES (2, 'Bob Dupont', 'bob@example.com', 'Lyon', 1230.00);\
INSERT OR IGNORE INTO clients VALUES (3, 'Claire Durand', 'claire@example.com', 'Paris', 8750.25);\
INSERT OR IGNORE INTO commandes VALUES (1, 1, 450.00, 'expédiée');\
INSERT OR IGNORE INTO commandes VALUES (2, 1, 320.50, 'expédiée');\
INSERT OR IGNORE INTO commandes VALUES (3, 2, 1230.00, 'validée');\
INSERT OR IGNORE INTO commandes VALUES (4, 3, 875.25, 'en_attente');\
'''); \
conn.close(); \
print('Demo database created: backend/demo.db')"

clean:  ## Remove build artifacts and cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	rm -f backend/.coverage
