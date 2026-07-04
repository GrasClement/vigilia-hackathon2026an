# Visuels des dashboards Grist

Construits dans l'interface Grist par MÉTIER (bloc B3), sans code — deux
mécanismes natifs de Grist suffisent pour tout ce qui suit : les **chart
widgets** pour les indicateurs d'agrégat, et les **linked widgets** pour la
navigation. Pas de widget custom dans le cœur du projet (décision "No-code
renforcé", `docs/architecture.md`) ; un widget sur mesure reste une
extension possible (B7.5), jamais requis pour la démo.

> sur les charts (`support.getgrist.com/widget-chart/`) et le linking de
> widgets (`support.getgrist.com/linking-widgets/`)

## Linked widgets — navigation (« résultats par veille / par texte / par auteur »)

Le mécanisme Grist de liaison de widgets ("Select by") : sélectionner une
ligne dans un widget filtre automatiquement un autre widget qui lui est
lié, sans formule ni code.

- **Résultats par veille** : un widget liste sur `veilles` (colonnes `id`,
  `type`, `objectif`, `actif`) lié à un widget détail sur `resultats`,
  filtré sur la veille sélectionnée. Colonnes affichées côté détail :
  `date_depot`, `auteur`, `texte_ref`, `extrait`, `url`, `sort`,
  `evolution`, `pertinent`. C'est la vue liée depuis chaque section du
  digest Tchap ("le reste dans Grist"), et le fait d'afficher `objectif`
  à côté de la sélection aide MÉTIER à juger la pertinence en contexte.
- **Résultats par texte** : même widget détail sur `resultats`, lié cette
  fois à un widget liste sur les valeurs distinctes de `texte_ref` — pour
  suivre tous les documents touchant un même dossier législatif
  indépendamment de la veille qui les a détectés.
- **Résultats par auteur** : même widget détail, lié à un widget liste sur
  `auteur` — utile pour les veilles de type `parlementaire` ou pour une
  lecture transverse ("qu'est-ce que ce parlementaire a déposé cette
  semaine, toutes veilles confondues").

## Chart widgets — tableau de bord (volumes et répartition)

Un chart widget par indicateur, posé sur la table `resultats` — pas de
formule, configuration graphique uniquement :

- **Volumes par jour** : nombre de lignes par `date_depot`, graphique en
  barres — repère visuel des pics de dépôt (PLF, fin de session). Un
  graphique temporel se prête mal à un camembert, rester en barres.
- **Répartition par `source`** : nombre de lignes par ressource
  Tricoteuses d'origine (`amendements`, `questions`, ...) une fois les
  extensions du bloc B7 activées — barres ou camembert selon le nombre de
  catégories (camembert lisible seulement si le nombre de sources reste
  faible).
- **Taux de pertinence** : proportion de `pertinent = oui` sur les lignes
  qualifiées, par veille, en barres — sert de signal pour ajuster les
  mots-clés, les exclusions et l'`objectif` d'une veille trop bruyante ou
  mal ciblée.

## Colonnes calculées

Territoire MÉTIER, sans toucher au dépôt de code (décision "No-code
renforcé") : lien cliquable construit depuis `uid` et `url`, compteur de
résultats par veille affiché directement dans la table `veilles` (formule
Python Grist référençant `resultats`).

## Extension B7.5 — widget Grist sur mesure

Si le temps le permet, un widget custom peut remplacer un ou plusieurs des
widgets standard ci-dessus (par exemple une vue de synthèse plus dense que
ce que les chart/linked widgets natifs permettent). Explicitement hors du
cœur du projet et de la décision "No-code renforcé" — voir
`docs/architecture.md`, bloc B7.

## Démo

La séquence de restitution (trois minutes, voir `docs/organisation.md`)
s'appuie directement sur ces widgets : ajout d'une veille en direct dans
la table `veilles` → `run.py` → digest dans Tchap → widget « Résultats par
veille » filtré sur la veille ajoutée, pour montrer le suivi du sort en
direct.
