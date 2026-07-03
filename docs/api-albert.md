# API Albert — synthèse du digest

Albert n'est plus utilisé comme moteur de recherche sémantique (la
recherche est déléguée à l'API Tricoteuses, voir `docs/api-tricoteuses.md`
et la décision "Matching" dans `docs/architecture.md`). Son seul usage
dans le pipeline est de produire, à chaque run, un paragraphe de synthèse
en français qui ouvre le digest Tchap (bloc B4).

Base URL : `https://albert.api.etalab.gouv.fr/v1` (`ALBERT_BASE_URL`).

Authentification : en-tête `Authorization: Bearer <ALBERT_API_KEY>`.

## Vérifier les quotas du compte

```
GET /v1/me/info
```

À appeler à J0 pour connaître les limites réelles du compte (offre
Expérimentation) avant le premier run en volume.

## Générer la synthèse (bloc B4)

```
POST /v1/chat/completions
```

Modèle : `Mistral-Small-3.2-24B` (quota Expérimentation : 50 req/min,
1 000 req/jour — un seul appel par run suffit très large).

Corps (schéma OpenAI-compatible) :

```json
{
  "model": "Mistral-Small-3.2-24B",
  "messages": [
    {"role": "system", "content": "Tu résumes en 3 à 5 phrases, en français, uniquement à partir des extraits fournis. N'invente aucun fait absent des extraits."},
    {"role": "user", "content": "<extraits du jour, regroupés par veille>"}
  ]
}
```

Règle de prompt : ne fournir que la colonne `extrait` des lignes de
`resultats` du jour (jamais le document complet), regroupées par veille.
Cela borne strictement ce que la synthèse peut affirmer — elle ne peut pas
introduire un fait hors des citations déjà sourcées dans Grist.

Le paragraphe produit s'ajoute en tête du digest (bloc B2), il ne
remplace jamais les extraits cités individuellement pour chaque alerte :
l'explicabilité native (citation systématique) reste la règle, la
synthèse n'est qu'un chapeau de lecture.

## Panne ou quota atteint

Le digest part quand même, sans le paragraphe de synthèse : les extraits
sourcés suffisent à eux seuls (voir Plans B, `docs/organisation.md`). Ne
jamais bloquer l'envoi du digest sur la disponibilité d'Albert.

## Historique — usage abandonné (recherche sémantique)

Les blocs d'ingestion de collection (`POST /v1/documents`,
`disable_chunking=true`) et de recherche hybride (`POST /v1/search`,
`method=hybrid`) ont été utilisés dans une version antérieure du pipeline
(voir `src/archive/match_semantique.py`) et sont abandonnés au profit de
la recherche server-side Tricoteuses. Conservés en archive pour mémoire,
pas dans le chemin principal.
