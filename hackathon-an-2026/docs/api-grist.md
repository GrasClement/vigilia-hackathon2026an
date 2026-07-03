# API Grist — configuration et résultats

Utilisée par `src/veille/grist.py` (bloc B1, lecture/écriture) et par
MÉTIER via l'interface Grist elle-même (bloc B3, aucun code). Client :
`requests` sur l'API REST de Grist, pas de bibliothèque tierce.

Instance : La Suite numérique — `GRIST_BASE_URL`
(`https://grist.numerique.gouv.fr` par défaut, voir `.env.example`).

Authentification : en-tête `Authorization: Bearer <GRIST_API_KEY>` sur
toutes les requêtes.

Document : `GRIST_DOC_ID` (l'identifiant du doc Grist créé au bloc B0),
présent dans l'URL de toutes les routes ci-dessous.

## Lire la table `veilles`

```
GET /api/docs/{GRIST_DOC_ID}/tables/veilles/records
```

Filtrer côté client sur `actif = true` (Grist ne fait pas de filtre
serveur simple sans passer par des vues filtrées). Colonnes du contrat :
`id`, `type`, `liste`, `actif`, `source`, `exclusion` — voir
`docs/architecture.md` pour le détail de chaque colonne.

## Écrire dans la table `resultats`

```
POST /api/docs/{GRIST_DOC_ID}/tables/resultats/records
```

Corps : `{"records": [{"fields": {...}}, ...]}`, par lots (éviter un appel
par ligne). Idempotence gérée côté application (B1) : avant d'insérer, on
vérifie que la paire `(uid, veille)` n'est pas déjà en base — Grist
lui-même n'a pas de contrainte d'unicité déclarative simple sur deux
colonnes.

## Mettre à jour une ligne existante (suivi du `sort`)

```
PATCH /api/docs/{GRIST_DOC_ID}/tables/resultats/records
```

Corps : `{"records": [{"id": <rowId>, "fields": {"sort": ..., "evolution": ...}}]}`.
Nécessite de connaître le `rowId` Grist de la ligne (obtenu à la lecture
initiale ou par une requête de lecture ciblée sur `uid` + `veille`).

## Colonne `pertinent`

Remplie à la main par MÉTIER directement dans l'interface Grist, jamais
par le pipeline. Le pipeline la lit seulement, pour le contrôle qualité
(bloc B3).

## Vues et tableau de bord

Construits dans l'interface Grist, sans appel API — voir
`docs/dashboards.md`.

## Bonnes pratiques

- Toujours paginer/lots-er les écritures (paramètre implicite : Grist
  accepte plusieurs `records` par requête, préférer des lots de quelques
  dizaines plutôt qu'un appel par ligne).
- Ne jamais committer `GRIST_API_KEY` ni `GRIST_DOC_ID` dans le dépôt —
  ils vivent dans `.env`, absent du contrôle de version (`.gitignore`).
- En cas d'erreur 429 (quota), backoff simple ; les volumes attendus (une
  poignée de veilles, quelques centaines de documents/jour en pic PLF)
  restent très en dessous des limites usuelles de l'instance.
