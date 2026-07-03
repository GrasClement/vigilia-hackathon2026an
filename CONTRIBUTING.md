# Contribuer

Avant d'écrire une ligne de code, lire `docs/architecture.md` : il définit
les contrats d'interface (document propre, tables Grist `veilles` et
`resultats`) et le découpage en blocs. Toute modification d'un contrat se
décide en synchro d'équipe et se consigne dans `DECISIONS.md`, jamais dans
un commit isolé.

## Branches

Une branche par bloc de travail, nommée `feature/<bloc>-<sujet>`.

Exemples : `feature/b1-recherche-grist`, `feature/b4-synthese-albert`

## Workflow

1. Ouvrir (ou prendre) l'issue GitHub correspondant au bloc
2. `git checkout -b feature/<bloc>-<sujet>`
3. Ouvrir la pull request en brouillon dès le premier commit, pas à la fin
4. Commits atomiques, message court et impératif (`add parsing csv`,
   `fix crash sur fichier vide`), pas de convention conventional-commits
5. Merge dans `main` dès que deux choses sont vraies : le code tourne sur
   un cas réel, et le contrat d'interface du bloc est respecté. Pas
   d'approbation formelle exigée au-delà de ça.

Le style est l'affaire de `ruff format` et `ruff check`, pas des relecteurs.

## Ce qu'on ne fait pas

- Pas de push direct sur `main`, pas de force-push
- Pas de commit de fichiers dans `data/`, de `.env`, ou de clés API
  (voir `.gitignore`)
- Pas de réouverture d'une décision actée dans `DECISIONS.md` sans synchro

## Setup local

```bash
git clone <url-du-depot> && cd veille-parlementaire
uv sync --all-extras
cp .env.example .env   # puis renseigner les clés
uv run pytest
```
