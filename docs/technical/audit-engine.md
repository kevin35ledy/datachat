# Moteur d'audit

## Vue d'ensemble

Le moteur d'audit analyse automatiquement une base de données selon 4 dimensions : sécurité, performance, qualité des données, et structure du schéma. Il retourne un rapport structuré avec des findings classés par sévérité et des recommandations actionnables.

## Architecture

```
POST /api/v1/audit (conn_id, audit_types)
    │
    ▼
AuditService.start_job()
    │
    ├── Celery task (async)
    │       │
    │       ├── SecurityAuditor.run()
    │       ├── PerformanceAuditor.run()
    │       ├── DataQualityAuditor.run()
    │       └── SchemaAuditor.run()
    │                 │
    │                 ▼
    │          [AuditFinding, ...]
    │
    ├── ReportBuilder.assemble()
    │       │
    │       ▼
    │   AuditReport (score + findings + recommendations LLM)
    │
    └── AuditRepository.save()

GET /api/v1/audit/{job_id}  → polling jusqu'à complétion
```

## Niveaux de sévérité

| Niveau | Couleur | Définition | Exemple |
|--------|---------|------------|---------|
| `critical` | Rouge | Risque immédiat, action requise sous 24h | Table passwords sans chiffrement |
| `high` | Orange | Risque significatif, action sous 1 semaine | Index manquant sur FK avec 1M+ lignes |
| `medium` | Jaune | Bonne pratique non respectée | Colonne email sans contrainte UNIQUE |
| `low` | Bleu | Optimisation recommandée | Convention de nommage incohérente |
| `info` | Gris | Observation sans impact direct | Table sans commentaire |

## Auditeur 1 — Sécurité

**Module** : `backend/app/services/audit/security.py`

### Vérifications effectuées

| Vérification | Sévérité | Méthode de détection |
|--------------|----------|---------------------|
| Colonnes potentiellement sensibles sans RLS | high | Noms de colonnes : password, secret, token, ssn, credit_card, api_key + vérification RLS (PostgreSQL) |
| User avec droits excessifs (non-SELECT) | high | Inspection des grants sur les tables |
| Tables accessibles sans authentification | critical | Vérification des politiques d'accès |
| Colonnes PII sans indication de chiffrement | medium | Détection de patterns : email, phone, birthdate, address |
| Procédures stockées avec SQL dynamique | medium | Analyse du code des procédures si disponible |
| Tables sans propriétaire défini | low | PostgreSQL : tables sans owner |
| Indexes sur colonnes sensibles exposant des données | medium | Index sur colonnes password/secret → leakage via explain |

### Exemple de finding

```json
{
  "id": "SEC-001",
  "audit_type": "security",
  "severity": "high",
  "title": "Colonne sensible potentiellement non protégée",
  "description": "La colonne 'users.password_hash' semble contenir des données sensibles mais aucune politique Row Level Security n'est activée sur cette table.",
  "affected_object": "users.password_hash",
  "recommendation": "Activer RLS sur la table users : ALTER TABLE users ENABLE ROW LEVEL SECURITY; et définir des politiques appropriées.",
  "evidence": {
    "column_name": "password_hash",
    "table": "users",
    "rls_enabled": false,
    "detected_patterns": ["password"]
  }
}
```

---

## Auditeur 2 — Performance

**Module** : `backend/app/services/audit/performance.py`

### Vérifications effectuées

| Vérification | Sévérité | Méthode |
|--------------|----------|---------|
| FK sans index de support | high | Pour chaque FK, vérifier l'existence d'un index sur la colonne FK |
| Table sans clé primaire | high | `WHERE table_name NOT IN (SELECT table_name FROM constraints WHERE type='PRIMARY KEY')` |
| Index dupliqués | medium | Deux index couvrant les mêmes colonnes dans le même ordre |
| Colonnes fréquemment filtrées sans index | medium | Via `pg_stat_user_tables` et `pg_stat_statements` si disponibles |
| Tables avec haute séquentialité de scan | medium | `pg_stat_user_tables.seq_scan >> idx_scan` |
| Index non utilisés | low | `pg_stat_user_indexes WHERE idx_scan = 0` |
| Tables sans statistiques à jour | low | Dernière exécution ANALYZE > 7 jours |

### Exemple de finding

```json
{
  "id": "PERF-003",
  "severity": "high",
  "title": "Clé étrangère sans index",
  "description": "La colonne commandes.client_id est une FK vers clients.id mais n'a pas d'index. Toute jointure entre ces tables nécessitera un sequential scan.",
  "affected_object": "commandes.client_id",
  "recommendation": "Créer un index : CREATE INDEX idx_commandes_client_id ON commandes(client_id);",
  "evidence": {
    "table": "commandes",
    "column": "client_id",
    "references": "clients.id",
    "table_row_count": 2847593,
    "estimated_join_cost_without_index": "high"
  }
}
```

---

## Auditeur 3 — Qualité des données

**Module** : `backend/app/services/audit/data_quality.py`

### Vérifications effectuées

| Vérification | Sévérité | SQL type |
|--------------|----------|----------|
| Taux de nulls élevé (> 30%) | medium | `COUNT(*) - COUNT(col)` / `COUNT(*)` |
| Doublons potentiels sur colonnes d'unicité | high | `GROUP BY + HAVING COUNT(*) > 1` |
| Violations de contrainte (données corrompues) | critical | `WHERE fk_col NOT IN (SELECT pk FROM parent)` |
| Colonnes email avec format invalide | medium | Regex basique sur le format email |
| Dates incohérentes | medium | `date_fin < date_debut`, dates futures aberrantes |
| Valeurs vides ≠ NULL | low | `WHERE col = ''` vs `WHERE col IS NULL` |
| Distribution anormale | low | Valeurs à > 3σ de la moyenne |

**Important** : Ces vérifications n'analysent pas toutes les lignes sur les grandes tables. Un sampling est appliqué (max 100,000 lignes par vérification).

### Exemple de finding

```json
{
  "id": "DQ-007",
  "severity": "medium",
  "title": "Taux de nulls élevé",
  "description": "La colonne clients.telephone a 67% de valeurs NULL (41,823 sur 62,421 lignes).",
  "affected_object": "clients.telephone",
  "recommendation": "Vérifier si cette colonne est réellement optionnelle. Si oui, documenter ce choix. Sinon, investiguer pourquoi les données manquent.",
  "evidence": {
    "null_count": 41823,
    "total_count": 62421,
    "null_percentage": 67.0
  }
}
```

---

## Auditeur 4 — Schéma

**Module** : `backend/app/services/audit/schema_audit.py`

### Vérifications effectuées

| Vérification | Sévérité |
|--------------|----------|
| Tables sans commentaire/description | info |
| Colonnes sans commentaire | info |
| Nommage incohérent (mélange snake_case/camelCase) | low |
| Tables orphelines (aucune FK entrante ni sortante) | low |
| Colonnes de type TEXT sur des données qui devraient être ENUM | low |
| Valeurs par défaut manquantes sur colonnes non-nullable | medium |
| PK en UUID sans index | medium |
| Colonnes JSON/JSONB sans validation de schéma | medium |
| Tables vides depuis longtemps | info |

---

## Format du rapport

```json
{
  "id": "audit_abc123",
  "conn_id": "conn_xyz",
  "created_at": "2026-03-22T14:30:00Z",
  "completed_at": "2026-03-22T14:32:45Z",
  "duration_seconds": 165,

  "scores": {
    "security": 62,       // 0-100, calculé selon sévérités
    "performance": 78,
    "data_quality": 85,
    "schema": 91,
    "overall": 79
  },

  "summary": {
    "total_findings": 23,
    "by_severity": {
      "critical": 1,
      "high": 4,
      "medium": 9,
      "low": 7,
      "info": 2
    }
  },

  "findings": [
    // Liste complète des AuditFinding triés par sévérité
  ],

  "llm_narrative": "Cette base présente un score de sécurité préoccupant (62/100). Le finding critique concerne..."
}
```

## Calcul du score

```python
SEVERITY_WEIGHTS = {"critical": -25, "high": -10, "medium": -5, "low": -2, "info": 0}

def calculate_score(findings: list[AuditFinding]) -> int:
    score = 100
    for finding in findings:
        score += SEVERITY_WEIGHTS[finding.severity]
    return max(0, min(100, score))
```

## Limites et précautions

- L'audit de qualité des données utilise un **sampling** — il peut manquer des problèmes dans des sous-ensembles de données
- Sur les bases de production, les requêtes d'audit sont exécutées avec une priorité basse (si supporté par le DB)
- Les vérifications de sécurité sont **statiques** (basées sur le schéma et les métadonnées) — elles ne testent pas activement les accès
- L'audit ne modifie jamais les données ou le schéma — toutes les vérifications sont en lecture seule
