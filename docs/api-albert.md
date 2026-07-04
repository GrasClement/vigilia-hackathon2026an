# API Albert — génération de la synthèse

Albert n'est plus utilisé comme moteur de recherche sémantique (la
recherche est déléguée à l'API Tricoteuses, voir `docs/api-tricoteuses.md`
et la décision "Matching" dans `docs/architecture.md`). Son usage dans le
pipeline (bloc B4) est de produire, à chaque run, le texte du paragraphe
de synthèse — rien de plus : B4 renvoie une chaîne de caractères, c'est
B5 (`docs/api-tchap-maubot.md`) qui l'ajoute au digest et l'envoie.

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

Corps (schéma OpenAI-compatible), gabarit défini par B2
(`docs/synthese-design.md`) :

```json
{
  "model": "Mistral-Small-3.2-24B",
  "messages": [
    {"role": "system", "content": "Tu résumes en 3 à 5 phrases, en français, uniquement à partir des extraits fournis. N'invente aucun fait absent des extraits. Relie les documents détectés à l'objectif déclaré par l'utilisateur quand il est renseigné."},
    {"role": "user", "content": "<par veille : objectif + extraits/evolution du jour>"}
  ]
}
```

Règle de prompt : ne fournir que les colonnes `extrait` et `evolution` des
lignes de `resultats` du jour (jamais le document complet), regroupées
par veille, plus la colonne `objectif` de chaque veille (table `veilles`,
peut être vide). Cela borne strictement ce que la synthèse peut
affirmer — elle ne peut pas introduire un fait hors des citations déjà
sourcées dans Grist, et elle est orientée par l'intention déclarée plutôt
que de produire un résumé générique.

B4 ne fait que générer ce texte. C'est B5 qui l'ajoute en tête du digest,
et qui décide de ne jamais remplacer les extraits cités individuellement
pour chaque alerte : l'explicabilité native (citation systématique) reste
la règle, la synthèse n'est qu'un chapeau de lecture.

## Panne ou quota atteint

B4 renvoie une chaîne vide plutôt que d'échouer. B5 envoie le digest quand
même, sans le paragraphe de synthèse : les extraits sourcés suffisent à
eux seuls (voir Plans B, `docs/organisation.md`). Ne jamais bloquer
l'envoi du digest sur la disponibilité d'Albert.

## Extension B7.2 — mode RAG sur les résultats accumulés

Les briques d'ingestion de collection (`POST /v1/documents`,
`disable_chunking=true`) et de recherche hybride (`POST /v1/search`,
method=hybrid`), utilisées dans une version antérieure du pipeline pour
le matching sémantique quotidien (voir `src/archive/match_semantique.py`),
sont abandonnées pour cet usage-là — la recherche du jour est déléguée à
l'API Tricoteuses.

Elles restent pertinentes pour une extension hors chemin critique (B7.2,
`docs/architecture.md`) : construire un index Albert sur l'historique
cumulé de `resultats`/`extrait` (pas les documents du jour, l'ensemble de
ce qui a déjà été détecté), pour permettre une interrogation ponctuelle
("qu'est-ce qu'on a vu sur ce sujet depuis un mois ?"). Le mode
conversationnel de B7.3 s'appuie sur cet index, restreint aux extraits
déjà sourcés — même principe d'explicabilité que B4.
