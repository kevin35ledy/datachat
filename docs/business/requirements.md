# Exigences fonctionnelles et non-fonctionnelles

## Exigences fonctionnelles

### F1 — Chat en langage naturel (PRIORITÉ 1)

| ID | Exigence | Critère d'acceptation |
|----|---------|----------------------|
| F1.1 | Un utilisateur peut poser une question en français ou anglais et obtenir des données | La question "Combien de clients avons-nous ?" retourne un nombre |
| F1.2 | Le SQL généré est affiché à l'utilisateur | L'UI montre le SQL dans un bloc collapsible avant/après les résultats |
| F1.3 | Une explication en langage naturel de la requête est fournie | "Cette requête compte le nombre total de lignes dans la table clients" |
| F1.4 | Le résultat est affiché sous forme de tableau paginé | Tableau avec en-têtes, tri par colonne, pagination 50/100/250 lignes |
| F1.5 | Le résultat peut être exporté en CSV ou JSON | Bouton "Exporter" disponible sur chaque résultat |
| F1.6 | Les questions de suivi maintiennent le contexte | "Et parmi eux, combien sont actifs ?" utilise le contexte de la question précédente |
| F1.7 | Un graphique est proposé quand pertinent | Une question sur l'évolution du CA affiche un graphique en ligne par défaut |

### F2 — Gestion des connexions (PRIORITÉ 1)

| ID | Exigence | Critère d'acceptation |
|----|---------|----------------------|
| F2.1 | Un utilisateur peut ajouter une connexion DB via un formulaire | Formulaire avec type de DB, host, port, user, password, database |
| F2.2 | La connexion peut être testée avant d'être sauvegardée | Bouton "Tester" affiche "Connexion OK" ou le message d'erreur |
| F2.3 | Les credentials sont stockés de manière chiffrée | Les credentials ne sont jamais lisibles en clair dans la base de l'app |
| F2.4 | L'utilisateur peut switcher entre plusieurs connexions | Sélecteur de connexion active dans la sidebar |
| F2.5 | Une connexion peut être modifiée ou supprimée | Actions disponibles sur chaque connexion |

### F3 — Explorateur de schéma (PRIORITÉ 2)

| ID | Exigence | Critère d'acceptation |
|----|---------|----------------------|
| F3.1 | Le schéma est affiché sous forme d'arbre navigable | Arbre : base → schémas → tables → colonnes |
| F3.2 | Les détails d'une table sont affichables | Colonnes, types, contraintes, index, FK, cardinalité |
| F3.3 | Un aperçu des données d'une table est disponible | 5 premières lignes affichées |
| F3.4 | Les relations FK sont visualisables graphiquement | Graphe de relations interactif |
| F3.5 | Le schéma peut être recherché par nom | Recherche temps réel sur tables et colonnes |

### F4 — Audit (PRIORITÉ 3)

| ID | Exigence | Critère d'acceptation |
|----|---------|----------------------|
| F4.1 | Un audit de sécurité peut être lancé | Détecte : colonnes sensibles sans restriction, manque de RLS, permissions excessives |
| F4.2 | Un audit de performance peut être lancé | Détecte : FK sans index, tables sans PK, requêtes lentes si logs disponibles |
| F4.3 | Un audit de qualité des données peut être lancé | Détecte : taux de nulls élevé, doublons potentiels, violations de contraintes |
| F4.4 | L'audit retourne un rapport structuré par sévérité | Findings classés : critique / élevé / moyen / faible / info |
| F4.5 | Chaque finding inclut une recommandation actionnable | "Ajouter un index sur commandes.client_id : `CREATE INDEX ...`" |
| F4.6 | L'audit s'exécute en arrière-plan sans bloquer l'UI | Indicateur de progression, résultats disponibles après complétion |

### F5 — Historique des requêtes (PRIORITÉ 2)

| ID | Exigence | Critère d'acceptation |
|----|---------|----------------------|
| F5.1 | Toutes les requêtes sont sauvegardées | Historique accessible depuis l'UI |
| F5.2 | Une requête passée peut être réexécutée | Bouton "Rejouer" sur chaque entrée d'historique |
| F5.3 | L'historique peut être filtré et recherché | Filtre par date, connexion, recherche texte |

---

## Exigences non-fonctionnelles

### NF1 — Performance

| Métrique | Cible | Conditions |
|---------|-------|------------|
| Temps de réponse P50 (requête simple) | < 3 secondes | Base locale, schéma < 50 tables |
| Temps de réponse P95 (requête complexe) | < 10 secondes | Incluant le temps LLM |
| Débit concurrent | 20 requêtes simultanées | Sans dégradation > 20% |
| Timeout DB hardcodé | 30 secondes | Non configurable par l'utilisateur |
| Limite de résultats | 1000 lignes | Configurable par admin |

### NF2 — Sécurité

| Exigence | Détail |
|---------|--------|
| SQL en lecture seule | Seuls les SELECT sont exécutables, défendu par 5 couches indépendantes |
| Credentials chiffrés | AES-256 au repos, jamais en clair dans les logs ou réponses API |
| Isolation des sessions | Chaque session utilisateur ne peut accéder qu'à ses propres connexions |
| Rate limiting | 60 requêtes/minute par utilisateur par défaut |
| Logs d'audit | Toutes les requêtes sont loggées avec timestamp, user, connexion, SQL |

### NF3 — Disponibilité et résilience

| Exigence | Détail |
|---------|--------|
| Disponibilité cible | 99.5% (hors maintenance planifiée) |
| Dégradation gracieuse LLM | Si le LLM est indisponible, l'UI affiche une erreur explicite (pas de crash) |
| Dégradation gracieuse Qdrant | Si Qdrant est indisponible, fallback sur envoi du schéma complet (si < seuil) |
| Retry LLM | 3 tentatives avec backoff exponentiel en cas d'erreur transitoire |

### NF4 — Compatibilité bases de données

| Base de données | Phase | Notes |
|----------------|-------|-------|
| PostgreSQL 13+ | 1 | Connecteur prioritaire |
| SQLite 3.35+ | 1 | Pour dev/tests |
| MySQL 8.0+ / MariaDB 10.6+ | 2 | |
| Fichiers CSV | 2 | Via DuckDB |
| MongoDB 6.0+ | 4 | Agrégation pipeline |
| BigQuery | 4 | Via google-cloud-bigquery |

### NF5 — Accessibilité et UX

| Exigence | Détail |
|---------|--------|
| Support multilingue UI | Français + Anglais minimum |
| Requêtes NL | Accepte le français et l'anglais |
| Responsive | Utilisable sur desktop (1920px) et laptop (1280px) |
| Accessibilité | WCAG 2.1 AA pour les composants principaux |
| Dark mode | Supporté via Tailwind |

### NF6 — Maintenabilité

| Exigence | Détail |
|---------|--------|
| Couverture de tests | ≥ 80% sur les services critiques (nl2sql, sql_validator) |
| Ajouter un connecteur DB | Un développeur doit pouvoir le faire en < 4 heures en suivant le guide |
| Ajouter un provider LLM | En < 1 heure en suivant le guide |
| Documentation API | OpenAPI auto-généré par FastAPI, toujours à jour |
