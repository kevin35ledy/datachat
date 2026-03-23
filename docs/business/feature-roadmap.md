# Roadmap des fonctionnalités

## Phase 1 — MVP NL2SQL (6-8 semaines)

**Objectif** : Démontrer la valeur principale. Un utilisateur peut se connecter à une base et poser des questions en langage naturel.

### Backend
- [ ] Skeleton FastAPI avec health endpoint et structure de projet complète
- [ ] `AbstractDatabaseConnector` Protocol (contrat central)
- [ ] `PostgreSQLConnector` (connecteur prioritaire)
- [ ] `SQLiteConnector` (pour dev/tests sans infrastructure)
- [ ] `AbstractLLMProvider` Protocol
- [ ] `AnthropicProvider` via LiteLLM (Claude Sonnet)
- [ ] `NL2SQLService` complet (10 étapes du pipeline)
- [ ] `SQLValidator` avec toutes les règles de sécurité
- [ ] `SchemaService` : introspection + embeddings Qdrant
- [ ] `PromptBuilder` : assemblage contexte schéma + historique
- [ ] `ResultFormatter` : structuration résultats + inférence graphique
- [ ] API endpoints : `/chat`, `/connections`, `/health`
- [ ] `QueryRepository` : sauvegarde historique requêtes
- [ ] `ConnectionRepository` : CRUD connexions avec chiffrement credentials
- [ ] SQLite pour la base de l'app en dev (pas d'infra PostgreSQL requise)
- [ ] Tests unitaires : SQLValidator, PromptBuilder, ResultFormatter
- [ ] Docker Compose minimal : API + Redis + Qdrant

### Frontend
- [ ] Scaffold React + Vite + TypeScript + Tailwind + shadcn/ui
- [ ] `Layout` : sidebar + zone principale
- [ ] `ConnectionsPage` : formulaire ajout connexion, test, liste
- [ ] `ChatPage` : `ChatWindow`, `QueryInput`, `MessageBubble`
- [ ] `SQLPreview` : bloc SQL collapsible avec coloration syntaxique
- [ ] `ResultTable` : tableau paginé avec tri
- [ ] `ThinkingIndicator` : animation pendant la génération
- [ ] Zustand stores : `connectionStore`, `chatStore`
- [ ] Client API typé axios

**Critère de sortie Phase 1** : Un utilisateur peut connecter une base PostgreSQL, taper "Combien y a-t-il de clients ?" et voir le résultat dans un tableau. Le SQL généré est visible.

---

## Phase 2 — Breadth + Streaming (4-5 semaines)

**Objectif** : Plus de sources de données, streaming temps réel, history, graphiques.

### Backend
- [ ] `MySQLConnector`
- [ ] `CSVConnector` (via DuckDB — permet d'interroger des fichiers CSV comme des tables)
- [ ] `OpenAIProvider` via LiteLLM
- [ ] `OllamaProvider` (LLM local)
- [ ] WebSocket endpoint `/ws/chat` avec streaming LLM
- [ ] `AnalysisService` : inférence de type de graphique, statistiques de base
- [ ] Rate limiting middleware
- [ ] Tests d'intégration multi-connecteurs

### Frontend
- [ ] `ResultChart` : Recharts (bar, line, scatter selon inférence)
- [ ] Streaming WebSocket : SQL s'affiche token par token
- [ ] `HistoryPage` : liste des requêtes passées, filtre, replay
- [ ] Export CSV/JSON sur les résultats
- [ ] `SettingsPage` : choix du provider LLM, modèle, paramètres
- [ ] Dark mode

**Critère de sortie Phase 2** : 3 connecteurs fonctionnels, streaming visible, historique consultable, graphiques générés automatiquement.

---

## Phase 3 — Schema Explorer + Audit (5-6 semaines)

**Objectif** : Deuxième set de fonctionnalités majeures — comprendre et auditer une base.

### Backend
- [ ] `SchemaPage` API : endpoints schéma détaillé par table
- [ ] `SchemaService.diff()` : détection de dérive de schéma entre snapshots
- [ ] `AuditService` orchestration + 4 auditeurs :
  - [ ] `SecurityAuditor` : permissions, données sensibles, RLS manquant
  - [ ] `PerformanceAuditor` : FK sans index, tables sans PK, slow queries
  - [ ] `DataQualityAuditor` : taux de nulls, doublons potentiels, violations
  - [ ] `SchemaAuditor` : conventions de nommage, orphelins, types incohérents
- [ ] Celery integration : jobs d'audit async
- [ ] `AuditRepository` : sauvegarde rapports
- [ ] PostgreSQL pour la base de l'app (Alembic migrations)
- [ ] LLM-generated remediation : chaque finding reçoit une recommendation SQL

### Frontend
- [ ] `SchemaPage` :
  - [ ] `SchemaTree` : arbre DB → tables → colonnes
  - [ ] `TableDetail` : colonnes, types, contraintes, index, FK, cardinalité
  - [ ] `SampleDataPreview` : 5 premières lignes
  - [ ] `RelationshipGraph` : React Flow, graphe FK interactif
  - [ ] `SchemaSearch` : recherche temps réel
- [ ] `AuditPage` :
  - [ ] `AuditTrigger` : sélection des types d'audit + lancement
  - [ ] Progress bar polling
  - [ ] `AuditSummary` : score cards par catégorie
  - [ ] `FindingsList` : filtrage par sévérité, tri
  - [ ] `FindingDetail` : modal avec recommendation SQL copiable

**Critère de sortie Phase 3** : Explorateur schéma complet avec graphe FK, audit complet avec rapport structuré et recommandations actionnables.

---

## Phase 4 — Production Ready (4-5 semaines)

**Objectif** : Le système est déployable pour une équipe en production.

### Backend
- [ ] Auth JWT : inscription, login, refresh token
- [ ] Multi-utilisateurs : isolation complète des connexions et sessions par user
- [ ] `BigQueryConnector` (google-cloud-bigquery)
- [ ] `MongoDBConnector` (moteur d'agrégation)
- [ ] Schema anonymization mode : alias des noms de colonnes dans les prompts
- [ ] Schema drift alerts : webhook/email quand dérive détectée
- [ ] Chiffrement renforcé des credentials (rotation de clé)
- [ ] RBAC basique : admin vs utilisateur standard
- [ ] Pentest du SQLValidator (suite de payloads adversariaux)
- [ ] Tests de performance : 100 requêtes concurrentes

### Frontend
- [ ] Pages login/inscription
- [ ] Gestion du compte utilisateur
- [ ] Admin panel : gestion des users, connexions globales

### Infrastructure
- [ ] Docker Compose production : reverse proxy, SSL, health checks
- [ ] Helm chart Kubernetes
- [ ] Variables d'environnement production documentées
- [ ] Monitoring : métriques Prometheus, dashboard Grafana

### Documentation
- [ ] Tous les fichiers `docs/` complétés
- [ ] Guide de déploiement production
- [ ] Guide de sécurité hardening

**Critère de sortie Phase 4** : Système multi-utilisateurs déployé en production avec auth, chiffrement, monitoring, et documentation complète.

---

## Backlog (post-Phase 4)

- **API publique** : permettre aux développeurs d'intégrer DataChat dans leurs outils via API
- **Plugins de connecteurs** : système de plugins pour que la communauté ajoute des connecteurs
- **Requêtes planifiées** : planifier des requêtes récurrentes et recevoir les résultats par email
- **Dashboards** : épingler des résultats de requêtes pour créer des dashboards dynamiques
- **Collaboration** : partager des sessions de chat, annoter des requêtes
- **Snowflake, Redshift, DuckDB** connectors
- **Mode exploration guidée** : le LLM propose des questions pertinentes basées sur le schéma
- **Fine-tuning** : utiliser le feedback (thumbs up/down) pour améliorer les prompts
