# Modèle de sécurité

## Principes généraux

DB-IA applique la défense en profondeur : plusieurs couches de sécurité indépendantes, de sorte qu'une seule défaillance ne compromet pas le système. Aucune requête générée par un LLM ne peut modifier ou supprimer des données, même si le LLM est manipulé.

## Modèle de menaces

### Menace 1 : Injection SQL via LLM (critique)

**Scénario** : Un utilisateur malveillant formule une requête en langage naturel conçue pour amener le LLM à générer du SQL destructeur (`DROP TABLE`, `DELETE FROM`, exfiltration via system tables).

**Défenses (toutes appliquées simultanément)** :

| Couche | Mécanisme | Contournement nécessaire |
|--------|-----------|--------------------------|
| 1 | sqlglot AST parse → type de statement | Trouver une faille dans sqlglot |
| 2 | Whitelist SELECT uniquement | ET la contourner |
| 3 | Transaction READ ONLY | ET convaincre le DB d'ignorer READ ONLY |
| 4 | User DB SELECT-only | ET avoir un user avec plus de droits |
| 5 | Blocklist system tables | ET accéder aux métadonnées sans les system tables |

Toutes les 5 couches doivent être contournées simultanément pour réussir l'attaque.

**Configuration recommandée pour le user de connexion DB** :
```sql
-- PostgreSQL — créer un user limité en lecture
CREATE USER dbia_query WITH PASSWORD 'xxx';
GRANT CONNECT ON DATABASE mydb TO dbia_query;
GRANT USAGE ON SCHEMA public TO dbia_query;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO dbia_query;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO dbia_query;
```

### Menace 2 : Hallucination LLM (résultats incorrects)

**Scénario** : Le LLM génère du SQL syntaxiquement valide mais sémantiquement incorrect (mauvaise table, mauvais filtre, jointure incorrecte).

**Défenses** :
- Schema RAG : les tables/colonnes dans le prompt viennent du schéma réel, pas de la mémoire du LLM
- Validation des références : après génération, toutes les tables et colonnes de la requête sont vérifiées contre le `SchemaInfo` introspectée
- Affichage du SQL : l'UI montre toujours le SQL généré avec son explication — les utilisateurs techniques peuvent le vérifier
- Feedback : boutons thumbs up/down pour signaler les résultats incorrects

### Menace 3 : Fuite du schéma vers une API tierce

**Scénario** : Des noms de tables/colonnes métier sensibles sont envoyés à l'API d'un LLM externe (Claude, OpenAI), constituant une fuite de données confidentielles.

**Défenses** :
- Schema RAG : seules les 10-15 tables pertinentes sont envoyées, pas le schéma entier
- Support Ollama : pour les environnements sensibles, utiliser un LLM local — aucune donnée ne quitte le réseau
- Audit trail : chaque appel LLM est loggé avec le contexte schéma envoyé
- Pas de données dans les prompts : les valeurs réelles des lignes ne sont jamais envoyées au LLM par défaut (les "sample rows" sont optionnels et désactivés par défaut)

### Menace 4 : Accès non autorisé aux connexions DB

**Scénario** : Les credentials de connexion stockés dans l'app sont volés (accès à la base de l'app, dump mémoire).

**Défenses** :
- Les credentials sont chiffrés au repos avec `SECRET_KEY` (Fernet/AES-256)
- La `SECRET_KEY` ne doit jamais être stockée dans la base de données
- Les credentials ne sont jamais retournés dans les réponses API
- Les logs ne contiennent jamais de credentials

### Menace 5 : Déni de service via requêtes coûteuses

**Scénario** : Un utilisateur génère des requêtes très lentes qui bloquent les ressources DB.

**Défenses** :
- Timeout 30 secondes sur toutes les requêtes
- `LIMIT {MAX_QUERY_ROWS}` injecté si absent
- Vérification de la complexité (profondeur de jointures, nombre de sous-requêtes)
- Rate limiting au niveau API (configurable par user)
- Pool de connexions limité par configuration

## Règles de sécurité SQL — référence complète

### Statements bloqués (whitelist)

Seul `SELECT` est autorisé. Sont bloqués :
- `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `UPSERT`
- `DROP`, `CREATE`, `ALTER`, `TRUNCATE`
- `GRANT`, `REVOKE`
- `EXEC`, `EXECUTE`, `CALL`
- `COPY` (PostgreSQL)
- `LOAD DATA` (MySQL)

### Tables système bloquées

Accès bloqué aux préfixes/schémas :
- `information_schema.*`
- `pg_catalog.*`, `pg_*`
- `mysql.*`, `sys.*`, `performance_schema.*`
- `sqlite_master`, `sqlite_sequence`

### Fonctions dangereuses bloquées

- `pg_read_file()`, `pg_ls_dir()`, `pg_exec()`
- `LOAD_FILE()` (MySQL)
- `system()`, `exec()`, `shell()`
- Tout appel de fonction définie par l'utilisateur (UDF) — bloqué par défaut, configurable

## Configuration de sécurité recommandée

### Environnement de développement

```bash
# DB user avec SELECT uniquement
DATABASE_QUERY_URL=postgresql://dbia_query:xxx@localhost/mydb

# Pas de chiffrement des credentials (dev)
SECRET_KEY=dev-not-secret-key
```

### Environnement de production

```bash
# User SELECT-only, connexion SSL obligatoire
DATABASE_QUERY_URL=postgresql://dbia_query:xxx@db:5432/mydb?sslmode=require

# Clé forte générée aléatoirement
SECRET_KEY=<64 bytes random hex>

# Limites conservatrices
MAX_QUERY_ROWS=500
QUERY_TIMEOUT_SECONDS=20

# LLM local pour données ultra-sensibles
LITELLM_DEFAULT_MODEL=ollama/llama3.1
```

### Isolation réseau recommandée

```
Internet
    │
    ▼
[Reverse Proxy / WAF]   ← Rate limiting, DDoS protection
    │
    ▼
[Frontend container]
    │
    ▼
[API container]         ← Seul container avec accès à la DB query user
    │
    ├──► [App DB]       ← Credentials chiffrés de l'app
    ├──► [Redis]        ← Pas d'accès externe
    ├──► [Qdrant]       ← Pas d'accès externe
    └──► [Target DB]    ← User SELECT-only, SSL
```

## Audit de sécurité de l'application

DB-IA elle-même peut être auditée par les outils qu'elle fournit — mais plus important, ces pratiques doivent être suivies :

- **Rotation des clés** : `SECRET_KEY` et `JWT_SECRET` doivent être rotés régulièrement
- **Logs d'accès** : toutes les requêtes NL, SQL générés, et résultats sont loggés (sans les credentials)
- **Mises à jour** : sqlglot, FastAPI, et les drivers DB doivent être mis à jour régulièrement (surface d'attaque)
- **Tests de pénétration** : le module `sql_validator.py` doit être testé avec une suite de payloads adversariaux à chaque version majeure
