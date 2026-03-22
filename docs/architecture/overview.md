# Architecture — Vue d'ensemble

## Diagramme en couches

```
┌──────────────────────────────────────────────────────────────┐
│                    Frontend (React + Vite)                   │
│   ChatPage | SchemaPage | AuditPage | ConnectionsPage        │
│   Zustand (UI state) + React Query (server state)            │
└────────────────────────────┬─────────────────────────────────┘
                             │ HTTP REST + WebSocket
┌────────────────────────────▼─────────────────────────────────┐
│                   API Layer (FastAPI)                        │
│   /api/v1/chat  /schema  /audit  /connections  /health       │
│   Validation Pydantic v2 — zéro logique métier              │
└──────┬──────────┬───────────┬─────────────────┬─────────────┘
       │          │           │                 │
┌──────▼───┐ ┌───▼──────┐ ┌──▼──────────┐ ┌───▼────────┐
│  NL2SQL  │ │  Schema  │ │    Audit    │ │  Analysis  │
│ Service  │ │ Service  │ │   Service   │ │  Service   │
│ 10 étapes│ │ + RAG    │ │ + Celery    │ │ + DuckDB   │
└──────┬───┘ └───┬──────┘ └──┬──────────┘ └────────────┘
       └─────────┴───────────┘
                    │
       ┌────────────┴────────────┐
       │                         │
┌──────▼──────────┐   ┌──────────▼──────────┐
│ LiteLLM Layer   │   │   Qdrant (vectors)  │
│ Claude/OAI/Llama│   │   Schema embeddings │
└─────────────────┘   └─────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────────┐
│              Database Connector Layer                        │
│         SQLAlchemy 2.x async + dialect drivers              │
│         ConnectorRegistry : scheme → implementation         │
└──────┬──────────┬──────────┬──────────┬──────────┬──────────┘
       ▼          ▼          ▼          ▼          ▼
  PostgreSQL    MySQL     SQLite     MongoDB      CSV
                                               (DuckDB)
```

## Responsabilités par couche

### Frontend (`frontend/src/`)

Interface utilisateur React. Responsabilités :
- Rendu des pages et composants
- Gestion de l'état UI local (Zustand)
- Cache des données serveur (React Query)
- Streaming WebSocket pour la génération SQL en temps réel
- Visualisation des résultats (Recharts)

**Ne contient jamais** : logique SQL, logique de validation, règles métier.

### API Layer (`backend/app/api/`)

Couche transport HTTP/WebSocket. Responsabilités :
- Réception et validation des requêtes entrantes (Pydantic)
- Routage vers le service approprié
- Sérialisation des réponses
- Gestion des erreurs HTTP

**Ne contient jamais** : logique métier, accès base de données, appels LLM directs.

### Services (`backend/app/services/`)

Logique métier et orchestration. Chaque service possède un domaine borné :

| Service | Domaine | Fichier principal |
|---------|---------|-------------------|
| `NL2SQLService` | Pipeline complet NL→SQL→résultat | `services/nl2sql/service.py` |
| `SchemaService` | Introspection, cache, embeddings schéma | `services/schema/service.py` |
| `AuditService` | Orchestration des 4 types d'audit | `services/audit/service.py` |
| `AnalysisService` | Analytics pandas/DuckDB, graphiques | `services/analysis/service.py` |
| `ChatService` | Sessions, historique, routing d'intention | `services/chat/service.py` |

### Core Domain (`backend/app/core/`)

Zéro dépendance externe. Contient uniquement :
- **Interfaces** (`core/interfaces/`) : Protocols Python pour DB Connector, LLM Provider, Embedder, Auditor
- **Modèles** (`core/models/`) : Pydantic domain models (pas des modèles ORM)
- **Exceptions** (`core/exceptions.py`) : hiérarchie d'exceptions de domaine

C'est le centre stable de l'application. Tout le reste dépend de ce module, mais ce module ne dépend de rien.

### Connecteurs (`backend/app/connectors/`)

Implémentations de `AbstractDatabaseConnector` par moteur de base de données. Chaque connecteur est auto-suffisant : il importe uniquement son driver + la classe de base.

Un `ConnectorRegistry` mappe les préfixes de connection string (`postgresql://`, `mysql://`, etc.) vers la classe d'implémentation.

### LLM Providers (`backend/app/llm/`)

Implémentations de `AbstractLLMProvider` par fournisseur. Tous passent par LiteLLM, ce qui les rend très fins. Le `LLMRegistry` mappe les noms de providers vers les classes.

### Workers (`backend/app/workers/`)

Tâches Celery pour les opérations longues. Les jobs d'audit s'exécutent de manière asynchrone : l'API retourne immédiatement un `job_id`, le client poll jusqu'à complétion.

## Flux de données principal

Voir [data-flow.md](data-flow.md) pour le détail complet du pipeline NL→SQL.

## Modèle de sécurité

Voir [security-model.md](security-model.md) pour le modèle de menaces et les défenses implémentées.

## Décisions architecturales

Voir le dossier [adr/](adr/) pour les Architecture Decision Records détaillant les choix techniques.
