# Guide de démarrage rapide

## Prérequis

- Python 3.11+
- Node.js 20+
- Docker + Docker Compose
- Une clé API Anthropic (`ANTHROPIC_API_KEY`)

## Installation en 5 minutes

### 1. Cloner et configurer l'environnement

```bash
git clone <repo>
cd datachat
cp .env.example .env
```

Éditer `.env` et renseigner au minimum :

```bash
ANTHROPIC_API_KEY=sk-ant-...
SECRET_KEY=<générer avec: python -c "import secrets; print(secrets.token_hex(32))">
```

### 2. Démarrer l'infrastructure

```bash
docker-compose up -d redis qdrant
```

Vérifier que les services sont up :
```bash
docker-compose ps
# redis et qdrant doivent être "healthy"
```

### 3. Démarrer le backend

```bash
cd backend
pip install uv
uv sync
uvicorn app.main:app --reload --port 8000
```

L'API est disponible sur http://localhost:8000
Documentation Swagger : http://localhost:8000/docs

### 4. Démarrer le frontend

```bash
cd frontend
npm install
npm run dev
```

L'application est disponible sur http://localhost:5173

### 5. Première requête

1. Ouvrir http://localhost:5173
2. Cliquer sur **"Ajouter une connexion"** dans la sidebar
3. Choisir le type **SQLite**
4. Renseigner le chemin vers un fichier SQLite (ex: `path/to/database.db`)
5. Cliquer **"Tester"** puis **"Sauvegarder"**
6. Sélectionner la connexion dans le sélecteur de la sidebar
7. Dans le chat, taper : *"Quelles tables y a-t-il dans cette base ?"*
8. Observer : le SQL généré, les résultats, et l'explication

## Tester avec une base de démonstration

Si vous n'avez pas de base sous la main, créez une base SQLite de test :

```python
# scripts/create_demo_db.py
import sqlite3

conn = sqlite3.connect("demo.db")
conn.executescript("""
CREATE TABLE clients (
    id INTEGER PRIMARY KEY,
    nom TEXT NOT NULL,
    email TEXT UNIQUE,
    ville TEXT,
    date_inscription DATE,
    ca_total REAL DEFAULT 0
);

CREATE TABLE commandes (
    id INTEGER PRIMARY KEY,
    client_id INTEGER REFERENCES clients(id),
    date_commande DATE,
    montant REAL,
    statut TEXT CHECK(statut IN ('en_attente', 'validée', 'expédiée', 'annulée'))
);

INSERT INTO clients VALUES
    (1, 'Alice Martin', 'alice@example.com', 'Paris', '2023-01-15', 5420.50),
    (2, 'Bob Dupont', 'bob@example.com', 'Lyon', '2023-03-22', 1230.00),
    (3, 'Claire Durand', 'claire@example.com', 'Paris', '2022-11-08', 8750.25);

INSERT INTO commandes VALUES
    (1, 1, '2024-01-10', 450.00, 'expédiée'),
    (2, 1, '2024-02-14', 320.50, 'expédiée'),
    (3, 2, '2024-01-28', 1230.00, 'validée'),
    (4, 3, '2024-03-01', 875.25, 'en_attente');
""")
conn.close()
print("Base de démo créée : demo.db")
```

```bash
python scripts/create_demo_db.py
```

Questions à essayer :
- "Combien de clients avons-nous ?"
- "Quels clients sont à Paris ?"
- "Quel est le montant total des commandes par client ?"
- "Montre-moi les commandes en attente"
- "Quel client a le plus dépensé ?"

## Résolution de problèmes courants

| Problème | Solution |
|---------|---------|
| `ANTHROPIC_API_KEY not found` | Vérifier que `.env` est renseigné et que `uvicorn` est lancé depuis `backend/` |
| Qdrant indisponible | `docker-compose up -d qdrant` et attendre 10 secondes |
| "Table inconnue" dans le chat | Cliquer "Rafraîchir le schéma" dans la connexion — les embeddings sont peut-être périmés |
| Frontend ne se connecte pas à l'API | Vérifier que l'API tourne sur le port 8000 (pas de conflit) |
