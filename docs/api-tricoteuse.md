# API Tricoteuses — acquisition et recherche

Utilisée par `src/veille/fetch_api.py` (bloc B1). Remplace l'acquisition
locale (clone Git, dump officiel) et le matching local : le filtre de date
et la recherche plein texte se font côté serveur, un appel par veille
suffit.

Documentation complète :
<https://parlement.tricoteuses.fr/docs#description/introduction>. Pour les
extensions (Sénat, autres ressources), s'y référer directement.

Base URL : `https://parlement.tricoteuses.fr/v2`

## Recherche par mot-clé avec plage de date

Paramètre `search` pour le mot-clé, plage de date sur le champ de date de
la ressource :

```
https://parlement.tricoteuses.fr/v2/<resource>?<dateField>.gte=2026-07-03T00:00:00.000Z&<dateField>.lte=2026-07-03T23:59:59.999Z&sort=<dateField>.desc&search=<keyword>&page=1&perPage=10
```

Le mot-clé est encodé URL (`budget vert` devient `budget%20vert`).

Exemple :

```
https://parlement.tricoteuses.fr/v2/amendements?dateDepot.gte=2026-07-03T00:00:00.000Z&dateDepot.lte=2026-07-03T23:59:59.999Z&sort=dateDepot.desc&search=budget&page=1&perPage=10
```

Le module `fetch_api.py` construit cette URL (`build_url`) et pagine
automatiquement (`fetch_jour`) ; `fetch_mots_cles` répète l'appel pour
chaque valeur de la colonne `liste` d'une veille et dédoublonne par `uid`.

## Ressources avec filtre de date — mapping utilisé par `veille.fetch_api.DATE_FIELDS`

| Ressource (`source` dans Grist) | Champ de date recommandé | Autres champs disponibles |
|---|---|---|
| `amendements` | `dateDepot` | `datePremierAjout`, `datePublication`, `dateSort` |
| `coSignatairesAmendement` | `amendementRef_dateDepot` | `datePremierAjout` |
| `coSignatairesDocument` | `dateCosignature` | `dateRetraitCosignature` |
| `documents` | `datePublication` | `dateCreation`, `dateDepot` |
| `questions` | `dateDepot` | `datePremierAjout`, `dateCloture` |
| `dossiers` | `dateDernierActe` | `dateDepot` |
| `actesLegislatifs` | `dateActe` | — |
| `etapesLegislatives` | `dateDebut` | `dateFin` |
| `scrutins` | `dateScrutin` | — |
| `reunions` | `dateSeance` | `timestampDebut`, `timestampFin` |
| `debats` | `dateSeance` | — |
| `interventions` | `dateSeance` | — |
| `paragraphes_directs` | `dateMaj` | — |
| `declarations` (HATVP) | `dateDepot` | — |
| `representantsInterets` (HATVP) | `dateCreation` | — |
| `personnes_auditionnees_reunions` | `dateNais` (date de naissance, à n'utiliser que si la veille filtre réellement sur ce critère) | — |

`votes` : pas de filtre de date direct. Passer par `scrutins` avec
`dateScrutin`, puis suivre les votes liés.

## Ressources sans filtre de date exposé

Recherche mot-clé et pagination disponibles, mais pas de `.gte`/`.lte`
utile pour une requête "du jour" : `acteurs`, `organes`, `mandats`,
`participants_reunions`, `auteursDocument`, `subdivisions`, `alineas`,
`votes`, `communes`, `adressesPostales`, `adressesElectroniques`,
`collaborateurs`, `groupesVotants`, `stats`, `statistiqueHebdomadaire`,
`metriques`, `liensAmitie`, `participantsDossiers`, `declarants`.

Ces ressources ne sont pas des valeurs valides pour la colonne `source`
d'une veille (voir `docs/architecture.md`, table `veilles`) : elles servent
au bloc B7 (extensions) ou à l'exploration ponctuelle, pas au pipeline
quotidien.

## Champ `source` de la table Grist `veilles`

Seules les ressources avec un champ de date exploitable ci-dessus sont
utilisables comme `source` d'une veille — c'est ce qui garantit que le
filtre "documents du jour" fonctionne. Valeurs courantes du hackathon :
`amendements` (mots-clés, parlementaires, dossiers) et `questions`
(extension B7.1).

## Points vérifiés au spike B0

À remplir pendant le spike sur `amendements` (voir `docs/architecture.md`,
bloc B0), sur un jour réel :

- [ ] Champs effectivement présents/absents par rapport au contrat "Item
  Tricoteuses" (`docs/architecture.md`) — lesquels manquent parfois,
  lesquels sont toujours vides
- [ ] Valeurs réelles observées pour `sort` (au-delà de "En traitement")
- [ ] Comportement de la pagination (`perPage`, nombre de pages sur un
  jour chargé type PLF) et latence mesurée d'un appel
- [ ] Cas particuliers rencontrés (amendements rectifiés, de suppression,
  de crédits) et leur incidence sur les champs `expose`/`dispositif`