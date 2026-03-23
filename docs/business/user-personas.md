# Personas utilisateurs

## Vue d'ensemble

DataChat cible 4 profils d'utilisateurs avec des besoins distincts. L'interface doit être accessible aux non-techniciens sans sacrifier la puissance pour les experts.

---

## Persona 1 — Sophie, Analyste Données

**Rôle** : Business Analyst dans une PME e-commerce
**Compétences techniques** : Maîtrise Excel, notions SQL basiques, à l'aise avec les outils no-code
**Objectif principal** : Répondre à des questions métier (CA, clients, produits) sans dépendre des développeurs

### Besoins

- Poser des questions en français : "Quels produits se vendent le mieux ce mois ?"
- Voir les résultats sous forme de tableau et de graphique
- Exporter les données pour les mettre dans un rapport PowerPoint
- Comprendre ce que le système a cherché (l'explication SQL en langage naturel)

### Frustrations actuelles

- Dépendance aux devs pour chaque nouvelle requête
- Outils BI trop complexes pour des questions ponctuelles
- Résultats qui arrivent trop tard

### Ce que DataChat lui apporte

- Autonomie complète sur les questions de données
- Résultats immédiats en langage naturel
- Export en un clic
- Pas besoin de comprendre le SQL

### Fonctionnalités prioritaires

1. Chat NL→résultat (F1)
2. Graphiques automatiques (F1.7)
3. Export CSV (F1.5)
4. Historique pour retrouver ses questions passées (F5)

---

## Persona 2 — Marc, Développeur Backend

**Rôle** : Senior Developer dans une startup SaaS
**Compétences techniques** : Expert SQL, Python, plusieurs SGBD maîtrisés
**Objectif principal** : Explorer rapidement des bases inconnues, debugger des problèmes de données

### Besoins

- Introspection rapide d'un nouveau schéma sans lire la doc
- Générer des requêtes d'exploration complexes rapidement
- Voir le SQL généré et pouvoir le modifier/copier
- Comprendre les relations FK d'une base legacy

### Frustrations actuelles

- Chaque nouvelle base = heure de lecture de schéma
- Les outils d'exploration sont trop GUI-centric (lents)
- Pas de moyen rapide d'auditer une base reprise en maintenance

### Ce que DataChat lui apporte

- Explorateur de schéma visuel avec graphe de relations
- Chat pour exploration rapide ("quelles tables ont une relation avec users ?")
- SQL toujours visible et copiable
- Audit automatique pour trouver les problèmes évidents

### Fonctionnalités prioritaires

1. Chat avec SQL visible (F1.2)
2. Explorateur de schéma + graphe FK (F3)
3. Audit performance (F4.2)
4. Copier le SQL pour l'utiliser dans son IDE

---

## Persona 3 — Isabelle, DBA

**Rôle** : Administratrice de bases de données dans un groupe industriel
**Compétences techniques** : Expert PostgreSQL, MySQL, Oracle. Maîtrise des index, plans d'exécution, sécurité
**Objectif principal** : Auditer et optimiser les bases, garantir la sécurité

### Besoins

- Audit automatisé de sécurité (permissions, données sensibles exposées)
- Détection d'index manquants et de requêtes lentes
- Rapport d'audit formaté pour la direction
- Détection de dérive de schéma entre environnements

### Frustrations actuelles

- Les audits manuels prennent des jours
- Pas d'outil unifié pour tous les types de DB
- Les rapports doivent être écrits manuellement

### Ce que DataChat lui apporte

- Audit automatisé en quelques minutes
- Rapport structuré avec sévérités et recommandations actionnables
- Support multi-DB unifié
- Détection de dérive de schéma

### Fonctionnalités prioritaires

1. Audit sécurité complet (F4.1)
2. Audit performance (F4.2)
3. Rapport exportable
4. Schema drift detection (Phase 3)

---

## Persona 4 — Thomas, Directeur Technique

**Rôle** : CTO d'une scale-up, 50 personnes
**Compétences techniques** : Connaissance générale, pas expert SQL
**Objectif principal** : Avoir une vue d'ensemble de l'état des données sans dépendre de l'équipe technique

### Besoins

- Questions métier de haut niveau : "Quel est notre taux de rétention client ?"
- Dashboard simple avec indicateurs clés
- Comprendre la santé globale de la base (résumé d'audit)
- Partager des résultats avec des non-techniciens

### Frustrations actuelles

- Les dashboards BI sont figés et ne répondent pas aux questions ad hoc
- Dépendance à l'équipe data pour chaque nouvelle métrique
- Les rapports d'audit techniques sont incompréhensibles

### Ce que DataChat lui apporte

- Questions ad hoc en langage naturel avec résultats immédiats
- Résumé d'audit en langage non-technique
- Graphiques partageables
- Autonomie sur ses propres questions

### Fonctionnalités prioritaires

1. Chat NL avec résumé en langage naturel (F1.3)
2. Graphiques (F1.7)
3. Résumé d'audit non-technique (F4)

---

## Matrice fonctionnalités × personas

| Fonctionnalité | Sophie (Analyste) | Marc (Dev) | Isabelle (DBA) | Thomas (CTO) |
|----------------|:-----------------:|:----------:|:--------------:|:------------:|
| Chat NL | ★★★ | ★★ | ★ | ★★★ |
| SQL visible/copiable | ★ | ★★★ | ★★ | — |
| Graphiques auto | ★★★ | ★ | — | ★★★ |
| Export CSV/JSON | ★★★ | ★★ | ★★ | ★ |
| Explorateur schéma | ★ | ★★★ | ★★★ | — |
| Graphe FK | — | ★★★ | ★★★ | — |
| Audit sécurité | — | ★ | ★★★ | ★★ |
| Audit performance | — | ★★ | ★★★ | ★ |
| Audit qualité données | ★★ | ★ | ★★★ | ★ |
| Historique requêtes | ★★★ | ★★ | ★ | ★★ |
| Schema drift | — | ★★ | ★★★ | — |

★★★ = critique  ★★ = important  ★ = utile  — = pas nécessaire
