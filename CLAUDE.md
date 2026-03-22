# CLAUDE.md — DB-IA : Guide du projet

> Ce fichier est la référence permanente pour tout développement assisté par IA sur ce projet.
> Il doit être lu en priorité et mis à jour à chaque décision architecturale significative.

---

## Vision du projet

DB-IA rend les bases de données accessibles à tous en traduisant le langage naturel en requêtes validées et sûres. Il permet aussi d'explorer le schéma d'une base et d'auditer sa sécurité, ses performances et la qualité de ses données — propulsé par n'importe quel LLM, connecté à n'importe quelle base de données.

**Promesse centrale** :
- Un utilisateur sans connaissance SQL doit pouvoir répondre à ses questions métier
- Un DBA doit pouvoir auditer un schéma sans écrire de requêtes d'audit manuelles
- Un développeur doit pouvoir brancher une nouvelle source de données en moins d'une heure

---

## Architecture en couches

```
┌──────────────────────────────────────────────────────────┐
│          React (Vite + TypeScript + Tailwind)            │
│    ChatPage | SchemaPage | AuditPage | ConnectionsPage   │
└─────────────────────────┬────────────────────────────────┘
                          │ REST + WebSocket
┌─────────────────────────▼────────────────────────────────┐
│              FastAPI + Pydantic v2                       │
│     /api/v1/chat  /schema  /audit  /connections          │
└──────┬──────────┬───────────┬────────────────────────────┘
       │          │           │
┌──────▼───┐ ┌───▼──────┐ ┌──▼──────────┐ ┌─────────────┐
│  NL2SQL  │ │  Schema  │ │    Audit    │ │  Analysis   │
│ Service  │ │ Service  │ │   Service   │ │   Service   │
└──────┬───┘ └───┬──────┘ └──┬──────────┘ └──────┬──────┘
       └─────────┴───────────┴────────────────────┘
                          │
┌─────────────────────────▼────────────────────────────────┐
│         LiteLLM (provider-agnostic)   Qdrant (RAG)       │
└─────────────────────────┬────────────────────────────────┘
                          │
┌─────────────────────────▼────────────────────────────────┐
│       SQLAlchemy 2.x async — Connector Layer             │
└────┬──────────┬──────────┬──────────┬────────────────────┘
     ▼          ▼          ▼          ▼
 PostgreSQL   MySQL     SQLite     MongoDB  CSV  BigQuery...
```

### 3 frontières inviolables

1. **Couche API** (`app/api/`) = zéro logique métier. Uniquement : validation input, appel service, sérialisation output.
2. **Core domain** (`app/core/`) = zéro dépendance externe. Uniquement des `Protocol` Python et des modèles Pydantic.
3. **SQL safety gate** : tout SQL généré par le LLM **doit** passer par `SQLValidator` avant exécution. Aucune exception. Jamais.

---

## Stack technique

| Couche | Technologie | Version | Raison |
|--------|-------------|---------|--------|
| API | FastAPI | ≥0.111 | Async-native, OpenAPI auto-généré |
| Validation | Pydantic | v2 | Typing strict, serialisation performante |
| LLM | LiteLLM | ≥1.40 | Interface unifiée 100+ providers |
| DB | SQLAlchemy | 2.x async | ORM universel + raw SQL |
| SQL Safety | sqlglot | ≥23 | Parsing AST dialect-aware (pas de regex) |
| Schema RAG | Qdrant | ≥1.9 | Vecteurs pour sélection tables pertinentes |
| Jobs async | Celery + Redis | — | Audit non-bloquant (peut durer minutes) |
| Analytics | pandas + DuckDB | — | In-process, rapide sur données moyennes |
| Frontend | React + Vite | React 18 | Standard industrie |
| Types TS | TypeScript | ≥5.3 | Strict mode activé |
| State UI | Zustand | ≥4 | Léger, pas de boilerplate |
| Server state | React Query | ≥5 | Cache, polling, revalidation |
| Viz | Recharts | ≥2.12 | Composable, React-natif, accessible |
| Style | Tailwind + shadcn/ui | — | Design system cohérent |

---

## Pipeline NL→SQL (10 étapes)

Toute requête en langage naturel passe par ces étapes dans l'ordre. Un échec à n'importe quelle étape retourne une erreur à l'utilisateur et n'atteint jamais l'exécution.

```
Entrée : "Montre-moi les 10 meilleurs clients par CA ce trimestre"

1. SCHEMA RAG      → embedding de la requête → top-k tables pertinentes (Qdrant)
2. PROMPT ASSEMBLY → schema context + historique conversation + règles sécurité
3. LLM GENERATION  → SQL + explication en langage naturel (LiteLLM)
4. SQL EXTRACTION  → isolation du bloc SQL dans la réponse LLM
5. SQLGLOT PARSE   → parsing AST — hard stop si SQL invalide syntaxiquement
6. SAFETY GATE     → whitelist SELECT uniquement, blocage system tables
7. TABLE VALIDATE  → vérification que toutes les tables/colonnes existent dans le schéma
8. COMPLEXITY CHECK→ estimation lignes, limite profondeur jointures
9. EXECUTION       → via connecteur, timeout 30s, LIMIT injecté si absent (max 1000)
10. FORMATTING     → table structurée + suggestion graphique + résumé NL

Sortie : {sql, explanation, result: {rows, columns}, chart_suggestion, summary}
```

### Règles de sécurité SQL non-négociables

- Seuls les statements `SELECT` peuvent s'exécuter
- `INSERT`, `UPDATE`, `DELETE`, `DROP`, `CREATE`, `TRUNCATE`, `EXEC`, `CALL` → erreur
- Accès à `information_schema`, `pg_catalog`, `mysql.user`, etc. → bloqué
- Toutes les requêtes s'exécutent dans une transaction `READ ONLY` si le connecteur le supporte
- Le user de connexion utilisé pour les requêtes NL **doit** avoir uniquement des droits `SELECT`
- Timeout 30 secondes hardcodé, non configurable via l'UI

---

## Ajouter un connecteur de base de données

1. Créer `backend/app/connectors/your_db.py`
2. Implémenter le Protocol `AbstractDatabaseConnector` (`app/core/interfaces/connector.py`)
3. Méthodes obligatoires :
   - `connect()` / `disconnect()` / `test_connection()`
   - `execute_query(sql, parameters, timeout_seconds)` → `QueryResult`
   - `introspect_schema()` → `SchemaInfo` (tables, colonnes, types, FK, index)
   - `explain_query(sql)` → plan d'exécution natif
   - `get_table_sample(table, limit)` → `QueryResult`
4. Définir la propriété `dialect` → string sqlglot du dialecte cible
5. Enregistrer dans `backend/app/connectors/registry.py` :
   ```python
   CONNECTOR_REGISTRY["yourdb"] = YourDBConnector
   ```
6. Ajouter les champs de connexion dans `frontend/src/components/connections/ConnectionForm.tsx`
7. Ajouter des tests d'intégration dans `backend/tests/integration/test_connectors.py`
8. Documenter dans `docs/guides/add-db-connector.md`

**Checklist PR** :
- [ ] 7 méthodes du Protocol implémentées
- [ ] Format de la connection string documenté dans la docstring
- [ ] `introspect_schema()` retourne les FK si le DB les supporte
- [ ] Gestion propre de l'épuisement du pool de connexions
- [ ] Tests passent avec SQLite in-memory en CI

---

## Ajouter un provider LLM

1. Créer `backend/app/llm/your_provider.py`
2. Étendre `BaseLLMProvider` (qui wrappe LiteLLM)
3. En général, seul le préfixe de modèle et les options provider-spécifiques doivent être personnalisés
4. Enregistrer dans `backend/app/llm/registry.py`
5. Ajouter la sélection du provider dans `frontend/src/pages/SettingsPage.tsx`
6. Documenter les variables d'environnement requises dans `.env.example`

La plupart des providers fonctionnent sans code additionnel si LiteLLM les supporte — il suffit d'un entry dans le registry.

---

## Conventions Python

- Python 3.11+, type hints stricts partout
- `async`/`await` systématique dans services et connecteurs
- Modèles Pydantic v2 pour toutes les données traversant les frontières de couches
- Pattern Repository pour tout accès à la base de l'app (pas de SQLAlchemy direct dans les services)
- Zéro logique métier dans les route handlers FastAPI
- Exceptions : lever des exceptions de domaine (`app/core/exceptions.py`), jamais des `HTTPException` depuis la couche service
- Logs : JSON structuré via `structlog`, toujours inclure `conn_id`, `session_id`, `query_id`
- Le mot `execute` dans le code doit déclencher une vérification : ce SQL a-t-il été validé ?

## Conventions TypeScript/React

- TypeScript strict, aucun `any` sans commentaire justificatif
- Tous les types API dans `api/types.ts` — miroir des modèles Pydantic
- Custom hooks pour tout data fetching — jamais de fetch/axios dans les composants
- Props des composants toujours typées via `interface`, pas de type inline
- `Zustand` pour l'état UI client, `React Query` pour l'état serveur (cache, polling)

---

## Variables d'environnement

```bash
# LLM
ANTHROPIC_API_KEY=                        # Requis pour démarrer
OPENAI_API_KEY=                           # Optionnel
LITELLM_DEFAULT_MODEL=claude-sonnet-4-6   # Modèle par défaut

# Vector Store
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=                           # Seulement pour Qdrant Cloud

# Base de l'application
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/dbia
# ou pour le dev local :
# DATABASE_URL=sqlite+aiosqlite:///./dbia.db

# Sécurité
SECRET_KEY=                               # Chiffrement credentials DB stockés
JWT_SECRET=                               # Auth utilisateurs (Phase 4)

# Redis (Celery)
REDIS_URL=redis://localhost:6379/0

# Limites
MAX_QUERY_ROWS=1000
QUERY_TIMEOUT_SECONDS=30
MAX_AUDIT_TABLES=500
```

---

## Commandes de développement

```bash
# Infrastructure (Redis + Qdrant)
docker-compose up -d redis qdrant

# Backend
cd backend
pip install uv && uv sync
uvicorn app.main:app --reload --port 8000

# Workers Celery (terminal séparé)
cd backend
celery -A app.workers.celery_app worker --loglevel=info

# Frontend
cd frontend
npm install
npm run dev   # → http://localhost:5173

# Tests
cd backend
pytest tests/unit -v                        # sans services externes
pytest tests/integration -v                 # nécessite Redis + Qdrant
pytest --cov=app --cov-report=html          # avec couverture
```

---

## Décisions architecturales clés

### Pourquoi sqlglot et pas regex pour valider le SQL ?
Les regex ne peuvent pas détecter de façon fiable les injections SQL obfusquées (commentaires, espaces, encodages). sqlglot parse vers un AST — les tricks d'obfuscation qui trompent les regex ne trompent pas un parser. Le type de statement est inspecté au niveau AST, pas par correspondance de chaîne.

### Pourquoi LiteLLM ?
Les APIs des providers changent constamment. LiteLLM fournit une interface stable : changer de provider = changement d'une ligne de config, pas de refactoring de code.

### Pourquoi Qdrant pour le schema RAG ?
Sur une base avec des centaines de tables, envoyer le schéma complet au LLM gaspille des tokens et dégrade la qualité. Embedder les descriptions tables/colonnes et récupérer uniquement les 10-20 tables pertinentes améliore significativement la précision SQL et réduit les coûts.

### Pourquoi Celery pour les audits ?
Un audit complet (qualité des données, analyse des index) peut durer plusieurs minutes sur un gros schéma. Celery permet de retourner immédiatement un job ID et de poller pour la complétion, sans bloquer la connexion HTTP.

### Pourquoi Zustand plutôt que Redux ?
La complexité du state frontend est modérée. Le boilerplate Redux n'est pas justifié. Zustand offre la même prévisibilité avec 80% de code en moins.

---

## Roadmap

| Phase | Contenu | Durée estimée |
|-------|---------|---------------|
| **1 — MVP NL2SQL** | Pipeline complet, PostgreSQL+SQLite, Claude, ChatPage | 6-8 sem. |
| **2 — Breadth** | MySQL/CSV, OpenAI/Ollama, streaming WS, historique, graphiques | 4-5 sem. |
| **3 — Explorer + Audit** | SchemaPage, 4 auditeurs, AuditPage, schema drift | 5-6 sem. |
| **4 — Production** | Auth JWT, BigQuery/MongoDB, chiffrement, Docker/K8s, docs | 4-5 sem. |

---

## Risques et mitigations

| Risque | Mitigation |
|--------|------------|
| SQL injection via LLM | sqlglot AST + whitelist SELECT + read-only transaction + credentials SELECT-only |
| Hallucination LLM | Schema RAG grounding + validation références tables dans AST + explication affichée |
| Fuite schéma vers API tierce | Support Ollama local + envoi top-k seulement (pas schéma entier) |
| Dépendance provider LLM | LiteLLM fallback routing + cache SQL requêtes répétées |
| Connecteur incomplet | Protocol strict + test harness standardisé + "known limitations" documentées |
