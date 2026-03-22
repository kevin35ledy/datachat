# Guide de sécurité — Environnements sensibles

## Déploiement avec données sensibles (santé, finance, RH)

### 1. Utiliser un LLM local (Ollama)

Empêche toute transmission du schéma ou des données à une API externe.

```bash
# Installer Ollama sur le serveur
curl -fsSL https://ollama.ai/install.sh | sh

# Télécharger un modèle orienté SQL
ollama pull sqlcoder

# Configurer DB-IA pour utiliser Ollama
LITELLM_DEFAULT_MODEL=ollama/sqlcoder
OLLAMA_API_BASE=http://localhost:11434
```

### 2. Créer des users DB en lecture seule

```sql
-- PostgreSQL
CREATE USER dbia_query WITH PASSWORD 'mot_de_passe_fort';
GRANT CONNECT ON DATABASE production TO dbia_query;
GRANT USAGE ON SCHEMA public TO dbia_query;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO dbia_query;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO dbia_query;
-- IMPORTANT: ne jamais donner SUPERUSER, CREATEDB, CREATEROLE

-- MySQL
CREATE USER 'dbia_query'@'app_host' IDENTIFIED BY 'mot_de_passe_fort';
GRANT SELECT ON production.* TO 'dbia_query'@'app_host';
FLUSH PRIVILEGES;
```

### 3. Chiffrement des credentials

```bash
# Générer une clé forte
SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# Stocker dans un gestionnaire de secrets (Vault, AWS Secrets Manager, etc.)
# Ne jamais mettre la clé dans le code ou dans le repo
```

### 4. Isolation réseau

```yaml
# docker-compose.production.yml — réseau isolé
networks:
  frontend:          # Frontend → API uniquement
  backend:           # API → DB, Redis, Qdrant
  db:               # DB isolée

services:
  api:
    networks: [frontend, backend]
  redis:
    networks: [backend]
    # Pas d'accès depuis l'extérieur
  qdrant:
    networks: [backend]
  target_db:
    networks: [db, backend]
```

### 5. Rate limiting strict

```bash
# Limiter les requêtes pour éviter l'exfiltration par volume
RATE_LIMIT_REQUESTS_PER_MINUTE=20    # Défaut: 60
RATE_LIMIT_REQUESTS_PER_HOUR=200     # Défaut: 1000
MAX_QUERY_ROWS=100                    # Défaut: 1000
```

### 6. Audit trail complet

```bash
# Activer les logs d'audit structurés
AUDIT_LOG_ENABLED=true
AUDIT_LOG_PATH=/var/log/dbia/audit.jsonl

# Chaque log inclura :
# - timestamp
# - user_id
# - conn_id
# - nl_query (question de l'utilisateur)
# - validated_sql (SQL exécuté)
# - row_count (nombre de lignes retournées)
# - execution_time_ms
# PAS les données retournées (trop volumineuses et potentiellement sensibles)
```

## Checklist de déploiement production

### Avant le déploiement

- [ ] `SECRET_KEY` générée aléatoirement et stockée dans un gestionnaire de secrets
- [ ] `JWT_SECRET` idem
- [ ] User DB avec droits SELECT uniquement créé
- [ ] Connexion DB en SSL (`?sslmode=require`)
- [ ] LiteLLM configuré avec fallback
- [ ] Redis protégé par mot de passe (`requirepass` dans redis.conf)
- [ ] Qdrant configuré avec API key

### Configuration SSL/TLS

```nginx
# Reverse proxy nginx
server {
    listen 443 ssl;
    ssl_certificate /etc/ssl/dbia.crt;
    ssl_certificate_key /etc/ssl/dbia.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;

    location /api/ {
        proxy_pass http://api:8000;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        root /app/frontend/dist;
        try_files $uri /index.html;
    }
}
```

### Variables d'environnement production

```bash
# Sécurité
SECRET_KEY=<64 bytes hex>
JWT_SECRET=<64 bytes hex>
JWT_EXPIRY_MINUTES=480           # 8 heures (pas de tokens qui expirent jamais)

# DB de l'app
DATABASE_URL=postgresql+asyncpg://dbia_app:xxx@db:5432/dbia?ssl=require

# Limites de sécurité
MAX_QUERY_ROWS=500
QUERY_TIMEOUT_SECONDS=20
MAX_AUDIT_TABLES=200             # Évite les audits trop longs

# Rate limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=30

# Désactiver les endpoints de debug
DEBUG=false
SHOW_SQL_ERRORS=false            # Ne pas exposer les messages d'erreur SQL en prod
```

## Maintenance de la sécurité

### Rotation des clés (mensuel recommandé)

```bash
# Générer une nouvelle clé
NEW_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# Mettre à jour dans le gestionnaire de secrets
# Redémarrer les services (les anciens tokens resteront valides jusqu'à expiration)
```

### Mise à jour des dépendances (hebdomadaire)

```bash
cd backend
uv lock --upgrade
# Vérifier les CVE sur les nouvelles versions

cd frontend
npm audit
npm audit fix
```

### Test de pénétration du SQLValidator (à chaque version majeure)

```python
# backend/tests/security/test_sql_injection.py
# Une suite de payloads adversariaux doit être testée avant chaque release :

ADVERSARIAL_PAYLOADS = [
    "SELECT * FROM users; DROP TABLE users;--",
    "SELECT * FROM information_schema.tables",
    "SELECT * FROM pg_catalog.pg_tables",
    "SELECT 1 UNION SELECT password FROM users",
    "SELECT/*comment*/1",
    "SELECT\t*\nFROM\rusers",
    # ... (liste complète dans le fichier de test)
]

@pytest.mark.parametrize("payload", ADVERSARIAL_PAYLOADS)
def test_sql_validator_blocks_injection(payload):
    with pytest.raises((SQLSecurityError, SQLValidationError)):
        SQLValidator().validate(payload, dialect="postgres")
```
