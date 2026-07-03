# Visuels des dashboards Grist

Construits dans l'interface Grist par MÉTIER (bloc B3), sans code ni
widget custom — les vues standard de Grist suffisent (décision "No-code
renforcé", `docs/architecture.md`).

## Vue « Résultats par veille »

Table `resultats` filtrée et groupée par `veille` (= `id` de la table
`veilles`), triée par `date_depot` décroissant. Colonnes affichées :
`date_depot`, `auteur`, `texte_ref`, `extrait`, `url`, `sort`,
`evolution`, `pertinent`. C'est la vue liée depuis chaque section du
digest Tchap ("le reste dans Grist").

## Vue « Résultats par texte »

Même table, groupée par `texte_ref`, pour suivre tous les documents
touchant un même dossier législatif indépendamment de la veille qui les a
détectés.

## Vue « Résultats par auteur »

Même table, groupée par `auteur`, utile pour les veilles de type
`parlementaire` ou pour une lecture transverse ("qu'est-ce que ce
parlementaire a déposé cette semaine, toutes veilles confondues").

## Tableau de bord — volumes et répartition

Un widget graphique Grist (chart natif, pas de custom widget) sur la
table `resultats` :

- **Volumes par jour** : nombre de lignes par `date_depot`, en barres —
  repère visuel des pics de dépôt (PLF, fin de session).
- **Répartition par `source`** : nombre de lignes par ressource
  Tricoteuses d'origine (`amendements`, `questions`, ...) une fois les
  extensions du bloc B6 activées.
- **Taux de pertinence** : proportion de `pertinent = oui` sur les lignes
  qualifiées, par veille — sert de signal pour ajuster les mots-clés et
  les exclusions d'une veille trop bruyante.

## Colonnes calculées

Territoire MÉTIER, sans toucher au dépôt de code (décision "No-code
renforcé") : lien cliquable construit depuis `uid` et `url`, compteur de
résultats par veille affiché directement dans la table `veilles` (formule
Python Grist référençant `resultats`).

## Démo

La séquence de restitution (trois minutes, voir `docs/organisation.md`)
s'appuie directement sur ces vues : ajout d'une veille en direct dans la
table `veilles` → `run.py` → digest dans Tchap → vue « Résultats par
veille » filtrée sur la veille ajoutée, pour montrer le suivi du sort en
direct.
