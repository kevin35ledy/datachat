# Flux de données — Pipeline NL→SQL→Résultat

## Vue d'ensemble

Ce document décrit le trajet complet d'une requête utilisateur, de la saisie en langage naturel jusqu'à l'affichage du résultat dans l'interface.

## Diagramme de séquence

```
Utilisateur          Frontend            API             NL2SQLService        LLM        Connecteur DB
    │                    │                │                    │               │               │
    │ "Top 10 clients     │                │                    │               │               │
    │  par CA ce trim."   │                │                    │               │               │
    ├───────────────────►│                │                    │               │               │
    │                    │ POST /chat     │                    │               │               │
    │                    ├───────────────►│                    │               │               │
    │                    │                │ process_message()  │               │               │
    │                    │                ├───────────────────►│               │               │
    │                    │                │                    │               │               │
    │                    │                │         ┌──────────┴───────────┐   │               │
    │                    │                │         │  1. SCHEMA RAG       │   │               │
    │                    │                │         │  embed(nl_text)      │   │               │
    │                    │                │         │  → top-k tables      │   │               │
    │                    │                │         └──────────┬───────────┘   │               │
    │                    │                │                    │               │               │
    │                    │                │         ┌──────────┴───────────┐   │               │
    │                    │                │         │  2. PROMPT ASSEMBLY  │   │               │
    │                    │                │         │  schema + historique │   │               │
    │                    │                │         │  + règles sécurité   │   │               │
    │                    │                │         └──────────┬───────────┘   │               │
    │                    │                │                    │               │               │
    │                    │                │         ┌──────────┴───────────┐   │               │
    │                    │                │         │  3. LLM GENERATION   │   │               │
    │                    │                │         │  complete(prompt)    ├──►│               │
    │                    │                │         │  ← SQL + explanation │◄──┤               │
    │                    │                │         └──────────┬───────────┘   │               │
    │                    │                │                    │               │               │
    │                    │                │         ┌──────────┴───────────┐   │               │
    │                    │                │         │  4. SQL EXTRACTION   │   │               │
    │                    │                │         │  parse LLM response  │   │               │
    │                    │                │         └──────────┬───────────┘   │               │
    │                    │                │                    │               │               │
    │                    │                │         ┌──────────┴───────────┐   │               │
    │                    │                │         │  5-8. VALIDATION     │   │               │
    │                    │                │         │  sqlglot AST parse   │   │               │
    │                    │                │         │  whitelist check     │   │               │
    │                    │                │         │  table references    │   │               │
    │                    │                │         │  complexity check    │   │               │
    │                    │                │         │  dialect translation │   │               │
    │                    │                │         └──────────┬───────────┘   │               │
    │                    │                │             [FAIL] │ [PASS]        │               │
    │                    │                │         ◄──────────┘               │               │
    │                    │                │                    │               │               │
    │                    │                │         ┌──────────┴───────────┐   │               │
    │                    │                │         │  9. EXECUTION        │   │               │
    │                    │                │         │  execute_query(sql)  ├───────────────────►
    │                    │                │         │  ← rows, metadata    │◄──────────────────┤
    │                    │                │         └──────────┬───────────┘   │               │
    │                    │                │                    │               │               │
    │                    │                │         ┌──────────┴───────────┐   │               │
    │                    │                │         │  10. FORMATTING      │   │               │
    │                    │                │         │  table structure     │   │               │
    │                    │                │         │  chart inference     │   │               │
    │                    │                │         │  NL summary          │   │               │
    │                    │                │         └──────────┬───────────┘   │               │
    │                    │                │                    │               │               │
    │                    │                │◄───────────────────┤               │               │
    │                    │◄───────────────┤                    │               │               │
    │◄───────────────────┤                │                    │               │               │
    │  Résultat affiché  │                │                    │               │               │
```

## Détail des 10 étapes

### Étape 1 — Schema RAG (Retrieval-Augmented Generation)

**Objectif** : Identifier les tables pertinentes sans envoyer le schéma entier au LLM.

- La requête NL est convertie en embedding vectoriel
- Qdrant retrouve le top-k des tables/colonnes dont la description est la plus proche
- Pour les petites bases (< 20 tables), toutes les tables sont envoyées directement
- Pour les grandes bases, seules les 10-15 tables les plus pertinentes sont sélectionnées

**Impact** : Réduit le coût LLM de 80% sur les grandes bases, améliore la précision SQL.

### Étape 2 — Prompt Assembly

**Objectif** : Construire un prompt structuré et complet pour le LLM.

Contenu du prompt :
```
SYSTEM:
  Tu es un expert SQL. Tu dois générer une requête SQL valide et sûre.
  Règles de sécurité: SELECT uniquement, pas de system tables, etc.
  Dialecte cible: {dialect}

SCHEMA:
  Table: clients (id INT PK, nom VARCHAR, ca_total DECIMAL, ...)
  Table: commandes (id INT PK, client_id FK→clients.id, date DATE, montant DECIMAL)
  [... top-k tables pertinentes ...]

CONVERSATION:
  [N derniers échanges pour la continuité contextuelle]

USER:
  "Top 10 clients par CA ce trimestre"

FORMAT ATTENDU:
  1. SQL entre balises <sql></sql>
  2. Explication en une phrase de ce que fait la requête
  3. Niveau de confiance (0-1)
```

### Étape 3 — LLM Generation

**Objectif** : Générer le SQL et son explication.

- Appel via LiteLLM → provider configuré (Claude, OpenAI, Ollama)
- Le LLM retourne : SQL brut, explication, niveau de confiance
- En mode streaming (WebSocket) : les tokens arrivent en temps réel dans l'UI

### Étape 4 — SQL Extraction

**Objectif** : Isoler proprement le SQL dans la réponse LLM.

- Parsing de la réponse pour extraire le contenu entre `<sql></sql>`
- Fallback : extraction du premier bloc de code si les balises sont absentes
- Nettoyage : suppression des backticks markdown, normalisation des espaces

### Étapes 5-8 — Validation (Safety Gate)

**Objectif** : Garantir qu'aucun SQL dangereux ne s'exécute.

| Vérification | Outil | Action si échec |
|--------------|-------|-----------------|
| Parsing syntaxique | sqlglot | Erreur "SQL invalide" |
| Type de statement | sqlglot AST | Erreur "seul SELECT autorisé" |
| System tables | Liste blocklist | Erreur "accès non autorisé" |
| Références tables/colonnes | SchemaInfo | Erreur "table inconnue: X" |
| Complexité (profondeur jointures) | Analyseur AST | Warning ou blocage configurable |
| Traduction dialecte | sqlglot.transpile() | SQL normalisé pour le DB cible |

Si **une seule** vérification échoue → retour d'erreur explicite à l'utilisateur, **aucune exécution**.

### Étape 9 — Execution

**Objectif** : Exécuter le SQL validé de manière sûre.

- Injection automatique de `LIMIT {MAX_QUERY_ROWS}` si absent
- Exécution dans une transaction `READ ONLY` si supporté par le connecteur
- Timeout hardcodé à 30 secondes (annulation si dépassé)
- Capture des métadonnées : `execution_time_ms`, `row_count`, `truncated`
- Sauvegarde dans le query history (`QueryRepository`)

### Étape 10 — Result Formatting

**Objectif** : Transformer le résultat brut en réponse enrichie.

- Structuration en `{columns: [...], rows: [...], total_count, truncated}`
- Inférence du type de graphique optimal selon la forme des données :
  - 1 colonne numérique + 1 colonne catégorielle → graphique barres
  - 1 colonne date + 1 colonne numérique → graphique ligne
  - 2+ colonnes numériques → scatter ou multi-barres
  - Texte seul → pas de graphique
- Génération d'un résumé NL en 1-2 phrases par le LLM (modèle léger)

## Variante WebSocket (streaming)

Pour améliorer la réactivité perçue :

```
1. Client ouvre WebSocket /ws/chat
2. Serveur envoie event: {type: "thinking"}
3. Serveur envoie events: {type: "schema_rag", tables: [...]}
4. LLM génère → serveur stream tokens: {type: "sql_token", token: "SELECT"}
5. Client affiche SQL en cours d'écriture
6. Serveur envoie: {type: "executing"}
7. Serveur envoie: {type: "result", data: {...}}
8. WebSocket reste ouvert pour les questions suivantes de la session
```

## Gestion des erreurs

| Étape | Erreur possible | Message utilisateur |
|-------|----------------|---------------------|
| RAG | Qdrant indisponible | "Service de recherche indisponible, retry" |
| LLM | API timeout/rate limit | "Le LLM ne répond pas, réessayez" |
| Validation | SQL non-SELECT | "Cette requête n'est pas autorisée" |
| Validation | Table inconnue | "La table 'X' n'existe pas dans ce schéma" |
| Execution | DB timeout | "Requête trop longue (>30s), affinez votre question" |
| Execution | Connexion perdue | "Connexion à la base perdue, reconnectez-vous" |
