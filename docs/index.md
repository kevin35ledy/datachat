# DataChat — Documentation

Bienvenue dans la documentation de **DataChat**, l'interface en langage naturel pour bases de données propulsée par LLM.

## Navigation rapide

| Section | Description |
|---------|-------------|
| [Démarrage rapide](guides/quick-start.md) | Installer et lancer DataChat en 5 minutes |
| [Architecture](architecture/overview.md) | Vue d'ensemble technique du système |
| [Pipeline NL→SQL](technical/nl2sql-pipeline.md) | Les 10 étapes de la traduction NL vers SQL |
| [Connecteurs DB](technical/database-connectors.md) | Sources de données supportées |
| [Providers LLM](technical/llm-providers.md) | LLM supportés et configuration |
| [Moteur d'audit](technical/audit-engine.md) | Fonctionnalités d'audit et interprétation |
| [Exigences métier](business/requirements.md) | Fonctionnalités et critères d'acceptation |
| [Roadmap](business/feature-roadmap.md) | Phases de développement |

## Qu'est-ce que DataChat ?

DataChat est une application web qui permet à n'importe quel utilisateur d'interroger une base de données en langage naturel — sans écrire de SQL. Un analyste peut poser une question en français, DataChat génère et exécute la requête sécurisée, et retourne les résultats sous forme de tableau ou graphique.

### Fonctionnalités principales

1. **Chat NL→SQL** — posez vos questions en langage naturel, obtenez des résultats
2. **Explorateur de schéma** — naviguez visuellement dans la structure de votre base
3. **Audit** — analyses automatiques de sécurité, performance, qualité des données
4. **Multi-sources** — changez de base de données sans changer de workflow
5. **Multi-LLM** — utilisez Claude, OpenAI, ou un modèle local (Ollama)

## Principes de conception

- **Source-agnostique** : changer de base de données = changement de configuration
- **LLM-agnostique** : changer de provider LLM = changement de configuration
- **Safety-first** : tout SQL généré est validé par un parser AST avant exécution
- **Progressive disclosure** : simple pour les non-techniciens, puissant pour les experts
