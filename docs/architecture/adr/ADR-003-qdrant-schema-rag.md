# ADR-003 — Schema RAG avec Qdrant

**Statut** : Accepté
**Date** : 2026-03-22

## Contexte

Sur les bases de données avec de nombreuses tables (50, 100, 500+), il est impossible d'envoyer le schéma complet au LLM à chaque requête. Le contexte serait saturé, les coûts exploseraient, et la précision du LLM se dégraderait avec un contexte trop large.

## Décision

Utiliser **Qdrant** comme vector store pour stocker les embeddings des tables et colonnes, et récupérer uniquement les tables pertinentes pour chaque requête (Retrieval-Augmented Generation sur le schéma).

## Fonctionnement

```
1. À la connexion à une base (ou après un refresh schéma) :
   → Introspection schéma complet
   → Pour chaque table : créer un document descriptif
     "Table clients: colonnes id (INT PK), nom (VARCHAR), email (VARCHAR),
      ca_total (DECIMAL), statut (ENUM: actif/inactif).
      Relations: commandes.client_id → clients.id"
   → Embed chaque document → stocker dans Qdrant (collection par conn_id)

2. À chaque requête NL :
   → Embed la requête de l'utilisateur
   → Qdrant similarity search → top-k tables (k=10-15 par défaut)
   → Seules ces tables sont incluses dans le prompt

3. Post-validation :
   → Si le LLM référence une table hors du top-k → erreur "table inconnue"
   → Optionnel : retry avec k élargi si la table manquante semble pertinente
```

## Alternatives considérées

### A. Schéma complet dans chaque prompt

**Rejeté** :
- 500 tables × ~100 tokens = 50,000 tokens par requête → coût prohibitif
- Le LLM se perd dans un contexte trop large
- Dépasse les limites de contexte des modèles moins puissants

### B. pgvector (extension PostgreSQL)

Stocker les embeddings dans la base PostgreSQL cible avec l'extension pgvector.

**Rejeté** :
- La base cible peut être MySQL, SQLite, MongoDB — pas forcément PostgreSQL
- Ajouter une extension à la base cible de l'utilisateur est intrusif
- Mélange les responsabilités (DB de l'app vs DB utilisateur)

### C. Chroma (vector store local)

Base de données vectorielle embarquée, pas de service séparé.

**Rejeté** :
- Moins adapté aux déploiements multi-instances (pas de partage d'état)
- Performance inférieure à Qdrant sur les grandes collections
- Mais : à considérer pour une version "single binary" future

### D. Qdrant (choisi)

**Avantages** :
- Service indépendant, scalable
- Performances excellentes (Rust)
- Collections isolées par connexion DB (`conn_id`)
- Filtrage par métadonnées (par schéma, par type de table)
- API simple, client Python bien maintenu
- Disponible en SaaS (Qdrant Cloud) ou auto-hébergé

**Inconvénients** :
- Service additionnel à opérer (Redis + Qdrant)
- Overhead pour les très petites bases (< 20 tables) — mitigé par bypass automatique

## Seuil de bypass RAG

Pour les bases avec moins de **20 tables**, le schéma complet est envoyé directement sans passer par Qdrant. Ce seuil est configurable (`SCHEMA_RAG_MIN_TABLES=20`).

## Conséquences

- `SchemaService` est responsable de maintenir les embeddings Qdrant à jour
- Un job Celery périodique (`refresh_schema_embeddings`) rafraîchit les embeddings quand le schéma change
- Les embeddings sont stockés en collection `schema_{conn_id}` dans Qdrant
- La qualité des embeddings est critique : les descriptions de tables doivent être riches (inclure des exemples de valeurs si disponibles)
