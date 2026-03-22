# ADR-001 — Validation SQL par parsing AST (sqlglot)

**Statut** : Accepté
**Date** : 2026-03-22

## Contexte

Tout SQL généré par un LLM doit être validé avant exécution. Nous avons besoin d'une méthode pour :
1. Vérifier que le statement est un SELECT (pas un DELETE, DROP, etc.)
2. Détecter les accès aux tables système
3. Détecter les fonctions dangereuses
4. Traduire le SQL vers le dialecte cible

## Décision

Utiliser **sqlglot** pour parser le SQL en AST (Abstract Syntax Tree) avant toute exécution.

## Alternatives considérées

### A. Validation par regex

```python
# Approche regex
if re.search(r'\b(DROP|DELETE|INSERT|UPDATE)\b', sql, re.IGNORECASE):
    raise SecurityError("Forbidden statement")
```

**Rejetée** : Les regex peuvent être contournées par obfuscation :
- `DR/*comment*/OP TABLE users` → regex ne détecte pas
- `SELECT * FROM users; DROP TABLE users` → dépend du regex
- Encodages unicode, commentaires imbriqués, retours à la ligne

### B. Exécution dans un sandbox

Exécuter dans une VM ou un container isolé avec un utilisateur sans droits.

**Rejetée** : Latence trop élevée (spin-up sandbox), complexité opérationnelle. La défense sur le user DB (SELECT-only) est suffisante comme couche complémentaire mais pas comme couche principale.

### C. sqlglot (choisi)

```python
import sqlglot

ast = sqlglot.parse_one(sql, dialect="postgres")
# Inspection du type de statement au niveau AST
if not isinstance(ast, sqlglot.expressions.Select):
    raise SecurityError("Only SELECT statements are allowed")
```

**Avantages** :
- Parse un vrai AST — imperméable à l'obfuscation
- Supporte 20+ dialectes SQL
- Peut transpiler entre dialectes : `sqlglot.transpile(sql, read="mysql", write="postgres")`
- Permet l'inspection des tables et colonnes référencées
- Bibliothèque pure Python, pas de dépendance système
- Maintenu activement, bonne couverture de test

**Inconvénients** :
- Peut rejeter du SQL valide non standard (rare)
- Ajoute ~5-10ms de latence par requête (acceptable)

## Conséquences

- `sql_validator.py` est le seul endroit où le SQL est inspecté — aucune autre couche ne doit faire de validation SQL
- Si sqlglot ne peut pas parser le SQL (syntaxe invalide), la requête est rejetée immédiatement
- La transpilation de dialecte est un effet de bord bénéfique : le SQL généré pour MySQL peut fonctionner sur PostgreSQL après transpilation
- Les tests de `sql_validator.py` doivent inclure une suite de payloads adversariaux (SQL injection classics)
