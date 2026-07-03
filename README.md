# Veille parlementaire

Veille ciblée sur les travaux de l'Assemblée nationale : chaque utilisateur
décrit ses sujets d'intérêt dans un tableau Grist (mot-clé, thème en
français, parlementaire, dossier) et reçoit chaque matin sur Tchap un digest
sourcé des documents qui le concernent, avec l'extrait justifiant chaque
alerte. Construit exclusivement sur l'open data de l'Assemblée et les
briques souveraines de l'État : Grist, Albert API, Tchap, hébergement
Onyxia.

## Installation

```bash
git clone <url-du-depot> && cd veille-parlementaire
uv sync --all-extras
cp .env.example .env   # puis renseigner les clés
```

Vérifier l'installation :

```bash
uv run pytest
```

## Lancer le pipeline

```bash
uv run run.py             # documents de la veille (j-1)
uv run run.py --date 2026-07-01
```

Le pipeline est idempotent : le relancer n'insère jamais de doublons.

## Documentation

- [`docs/architecture.md`](docs/architecture.md) — contrats d'interface,
  blocs de travail, décisions. **À lire avant d'écrire du code.**
- [`docs/organisation.md`](docs/organisation.md) — rôles, rythme,
  workflow de contribution.
- [`DECISIONS.md`](DECISIONS.md) — journal des décisions.

## Contribuer

Une issue par bloc de travail, branche `feature/<bloc>-<sujet>`, merge
request ouverte en brouillon dès le premier commit. La review vérifie deux
choses : le code tourne sur un cas réel, et le contrat d'interface est
respecté. Le style est l'affaire de `ruff format` et `ruff check`, pas des
relecteurs.

## Structure

```
src/veille/
├── config.py            # URLs, constantes, lecture de l'environnement
├── fetch.py             # B1 — acquisition (Tricoteuses, fallback dump AN)
├── clean.py             # B2 — extraction et nettoyage du texte
├── match_lexical.py     # B3 — veilles mot_cle (+ exclusions)
├── match_meta.py        # B3 — veilles parlementaire / dossier
├── match_semantique.py  # B4 — veilles theme via Albert API
├── grist.py             # B5 — lecture des veilles, écriture des résultats
└── digest.py            # B6 — digest quotidien envoyé sur Tchap
run.py                   # B9 — orchestration
```

## Licence

MIT.
