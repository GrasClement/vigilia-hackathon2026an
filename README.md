# Veille parlementaire

Veille ciblée sur les travaux de l'Assemblée nationale : chaque utilisateur
décrit ses sujets d'intérêt dans un tableau Grist (mot-clé, sujet en
français, parlementaire, dossier) et reçoit chaque matin sur Tchap un digest
sourcé et synthétisé des documents qui le concernent, avec l'extrait
justifiant chaque alerte. La recherche s'appuie sur l'API Tricoteuses
(open data de l'Assemblée) et les briques souveraines de l'État : Grist,
Albert API (synthèse), Tchap, hébergement Onyxia.

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
  blocs de travail, décisions, flux dans l'architecture. **À lire avant
  d'écrire du code.**
- [`docs/organisation.md`](docs/organisation.md) — rôles, rythme,
  workflow de contribution.
- [`docs/api-tricoteuses.md`](docs/api-tricoteuses.md) — acquisition et
  recherche server-side.
- [`docs/api-grist.md`](docs/api-grist.md) — lecture des veilles,
  écriture des résultats.
- [`docs/api-albert.md`](docs/api-albert.md) — synthèse du digest.
- [`docs/api-tchap-maubot.md`](docs/api-tchap-maubot.md) — diffusion du
  digest.
- [`docs/dashboards.md`](docs/dashboards.md) — vues et tableau de bord
  Grist.
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
├── config.py           # URLs, constantes, lecture de l'environnement
├── fetch_api.py         # B1 — recherche via l'API Tricoteuses (par veille)
├── grist.py             # B1 — lecture des veilles, écriture des résultats
├── digest.py            # B2 — digest quotidien envoyé sur Tchap
└── albert.py            # B4 — synthèse du digest via l'API Albert
run.py                   # B5 — orchestration
src/archive/               # anciens blocs d'acquisition/nettoyage/matching
                            # local, abandonnés au profit de la recherche
                            # server-side Tricoteuses (voir docs/architecture.md)
```

## Licence

MIT.
