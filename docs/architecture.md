# Veille parlementaire — Architecture et découpage en blocs

Version révisée : suivi du sort séparé de la recherche (B1/B1.5), la
synthèse Albert se pense (B2), se génère (B4) et se publie (B5) dans trois
blocs distincts, pilotée par un nouveau champ `objectif` sur chaque veille.
Ce document est la référence du dépôt : tout nouveau contributeur le lit
avant d'écrire une ligne de code. Il définit les contrats d'interface, les
blocs de travail (tâches, outils, besoins, profil requis, dépendances) et
les décisions d'architecture actées.

## Le projet en trois phrases

Chaque administration, chercheur ou citoyen décrit ses sujets d'intérêt —
et *pourquoi* ils l'intéressent — dans un tableau Grist (mot-clé, sujet en
français, parlementaire ou dossier, plus un objectif en une phrase), et
reçoit chaque matin sur Tchap un digest sourcé des travaux de l'Assemblée
qui le concernent, avec l'extrait qui justifie chaque alerte et un
paragraphe de synthèse généré par Albert à partir de cet objectif. Le
système suit également le devenir des documents détectés (amendement
adopté, rejeté). Tout repose sur l'open data de l'Assemblée via l'API
Tricoteuses et les briques souveraines de l'État : Grist, Albert API,
Tchap (via maubot), hébergement Onyxia.

## Flux dans l'architecture

```
Grist (table veilles)                       API Tricoteuses (v2)
  id / type / liste / actif / source /  ──────►  recherche + filtre de date
  exclusion / objectif                            par ressource (amendements,
        │                                         questions, documents, ...)
        │  B1 lit les veilles actives                    │
        ▼                                                ▼
                    B1 — un appel par veille active
                    (source, liste de mots-clés, jour)
                              │
                filtrage local des `exclusion`
                              │
                              ▼
              Grist (table resultats) — nouvelles lignes
                uid / veille / extrait / sort / ...
                              │
                              ▼
              B1.5 — suivi du sort (uid déjà en base)
                 met à jour `sort` et `evolution`
                              │
                              ▼
              B4 — génération de la synthèse (Albert)
          (gabarit défini par B2 ; `objectif` de chaque
           veille [B3] + `extrait`/`evolution` du jour)
                              │
                              ▼
              B5 — publication du digest (Tchap)
          (synthèse de B4 en tête + top par veille +
                 évolutions + liens Grist)
                              │
                              ▼
                Tchap (salon de diffusion)
```

B2 (design de la synthèse) et B3 (configuration Grist) n'apparaissent pas
comme des étapes d'exécution : ce sont des contrats d'entrée, pas du code
dans le chemin du run — B2 fournit le gabarit que B4 implémente, B3
fournit les veilles (dont `objectif`) et les vues de consultation.

Le détail de chaque API (paramètres, quotas, endpoints réellement
appelés) est dans un document dédié :

- [`docs/api-tricoteuses.md`](api-tricoteuses.md) — acquisition et
  recherche server-side (B1)
- [`docs/api-grist.md`](api-grist.md) — lecture des veilles, écriture et
  mise à jour des résultats (B1, B1.5, B3)
- [`docs/synthese-design.md`](synthese-design.md) — design de la synthèse
  (B2)
- [`docs/api-albert.md`](api-albert.md) — génération de la synthèse (B4)
- [`docs/api-tchap-maubot.md`](api-tchap-maubot.md) — publication du
  digest (B5)
- [`docs/dashboards.md`](dashboards.md) — vues et tableau de bord Grist
  (B3)

## Flux dans l'architecture

```
Grist (table veilles)                     API Tricoteuses (v2)
  id / type / liste / actif /    ──────►    recherche + filtre de date
  source / exclusion                         par ressource (amendements,
        │                                    questions, documents, ...)
        │  B1 lit les veilles actives              │
        ▼                                          ▼
                    B1 — un appel par veille active
                    (source, liste de mots-clés, jour)
                              │
                filtrage local des `exclusion`
                              │
                              ▼
                    Grist (table resultats)
                 uid / veille / extrait / evolution / ...
                              │
              ┌───────────────┴───────────────┐
              ▼                                ▼
     B4 — synthèse Albert                B2 — digest Tchap
   (chat completion sur les          (top par veille + section
    extraits du jour, 3-5 phrases)    évolutions + synthèse en tête)
              │                                │
              └────────────► Tchap (salon de diffusion) ◄────────────┘
```

Le détail de chaque API (paramètres, quotas, endpoints réellement
appelés) est dans un document dédié :

- [`docs/api-tricoteuses.md`](api-tricoteuses.md) — acquisition et
  recherche server-side (B1)
- [`docs/api-grist.md`](api-grist.md) — lecture des veilles, écriture des
  résultats (B1, B3)
- [`docs/api-albert.md`](api-albert.md) — synthèse du digest (B4)
- [`docs/api-tchap-maubot.md`](api-tchap-maubot.md) — envoi du digest (B2)
- [`docs/dashboards.md`](dashboards.md) — vues et tableau de bord Grist (B3)

## Profils de contributeurs

- `DEV` : Python confirmé. Prend les blocs qui touchent aux API externes
  (Tricoteuses, Grist, Albert, Tchap) et à l'assemblage.
- `DATA` : à l'aise en notebook, code débutant à intermédiaire. Prend
  l'écriture Grist, le suivi du sort, la génération de la synthèse Albert.
- `MÉTIER` : connaissance de l'Assemblée et de ses textes, pas de code.
  Prend la configuration Grist, la qualification des résultats, la
  conception et la publication du digest. Ce profil porte la
  démonstration "no code" : tout ce qu'il fait doit être faisable par un
  futur utilisateur sans développeur.

## Contrats d'interface

Ces deux tables sont l'épine dorsale du projet. Un bloc peut être réécrit
entièrement sans toucher aux autres tant qu'il respecte son contrat. Toute
modification d'un contrat se décide en synchro d'équipe et se consigne dans
DECISIONS.md — jamais dans un commit isolé.

### Item Tricoteuses — sortie de l'API, entrée de B1

L'API Tricoteuses livre déjà un texte propre (JSON éclaté, un objet par
document) : il n'y a plus d'étape de nettoyage local. B1 fait un mapping
direct des champs utiles, sans extraction HTML :

```python
{"uid": str,          # identifiant AN, ex. AMANR5L17PO838901B1906P1D1N001548
 "numero": str,        # numéro d'amendement (ou de document) lisible
 "auteur": str,        # nom complet de l'auteur principal
 "texte_ref": str,     # référence du texte législatif visé
 "date_depot": str,    # ISO YYYY-MM-DD
 "place": str,         # division visée, ex. "Article 2 bis"
 "sort": str,          # sort si voté, sinon état ("En traitement")
 "url": str,           # assemblee-nationale.fr/dyn/{leg}/amendements/{uid}
 "expose": str,        # exposé des motifs
 "dispositif": str}    # dispositif
```

Le détail des champs disponibles par ressource (amendements, questions,
documents, dossiers...) est documenté dans `docs/api-tricoteuses.md`.

### Table Grist `veilles` — éditée par MÉTIER (B3), lue par B1 et B4

```
id | type | liste | actif | source | exclusion | objectif
```

- `id` : identifiant de la veille, choisi par MÉTIER (ex. `fiscalite-verte`).
- `type` : quatre valeurs possibles —
  - `mot_cle` : un ou plusieurs mots-clés (recherche plein texte
    Tricoteuses, insensible à la casse) ;
  - `sujet` : description courte en français d'un sujet d'intérêt,
    passée telle quelle en recherche plein texte Tricoteuses ;
  - `parlementaire` : nom du parlementaire à suivre ;
  - `dossier` : référence du dossier ou du texte législatif à suivre.
- `liste` : les valeurs recherchées pour cette veille, séparées par des
  virgules (variantes d'un mot-clé, ou une seule valeur pour
  parlementaire/dossier).
- `actif` : booléen (case à cocher Grist). Permet de suspendre une veille
  sans la supprimer.
- `source` : ressource Tricoteuses interrogée — `amendements`, `questions`,
  `documents`, `dossiers`, etc. (voir la liste complète dans
  `docs/api-tricoteuses.md`).
- `exclusion` : terme(s), séparés par des virgules, qui annulent un
  résultat quand ils sont présents dans le texte du document. C'est le
  seul filtrage encore fait côté client — l'API Tricoteuses n'a pas
  d'opérateur "NOT" dans sa recherche.
- `objectif` : texte libre en français décrivant l'intention de la veille
  (ex. *"repérer les impacts budgétaires pour anticiper les amendements de
  crédits"*). Fourni tel quel dans le prompt de B4 (voir
  `docs/synthese-design.md` et `docs/api-albert.md`) : c'est ce qui permet
  à la synthèse de dire *pourquoi* un document compte, pas seulement
  *qu'il existe*. Un champ vide reste valide — la synthèse retombe alors
  sur un résumé neutre des extraits.

### Table Grist `resultats` — écrite par B1, mise à jour par B1.5, lue par B4, B5 et les vues

```
uid | veille | extrait | evolution | texte_ref | auteur | date_depot |
sort | url | pertinent
```

- Une ligne par paire document × veille ; un document touchant deux
  veilles produit deux lignes, chacune avec son extrait. C'est voulu.
- `extrait` : la justification, toujours citée depuis le document —
  phrase de l'exposé ou du dispositif contenant le terme recherché (ou,
  pour `parlementaire`/`dossier`, le champ matché). L'explicabilité est
  native, jamais générée seule ; la synthèse d'Albert (B4) s'ajoute au
  digest à côté de l'extrait, elle ne le remplace jamais.
- `evolution` : renseignée par B1.5 quand le `sort` change après détection
  ("adopté le JJ/MM"). C'est le suivi du devenir, alimenté gratuitement
  par le rappel quotidien de l'API sur les mêmes `uid`.
- `pertinent` : oui/non/vide, rempli à la main par MÉTIER. C'est la
  vérité terrain utilisée pour ajuster les veilles (mots-clés, exclusions,
  objectif).
- Hiérarchisation : tri par `date_depot` dans le digest et les vues ; pas
  de score numérique à maintenir, la recherche server-side ne renvoie pas
  de pertinence graduée sur laquelle s'appuyer.

## Blocs de travail

Une issue GitHub par bloc ; les tâches ci-dessous en sont la checklist.
Branches `feature/<bloc>-<sujet>`, PR vers main, merge par l'intégrateur.

### B0 — Socle du dépôt · DEV · à faire avant le hackathon

- pyproject.toml géré par UV, ruff (format + check), layout `src/veille/`,
  `data/` et `.env` dans le .gitignore
- `.env.example` documentant : `ALBERT_API_KEY`, `GRIST_API_KEY`,
  `GRIST_DOC_ID`, `TCHAP_BOT_MATRIX_ID`, `TCHAP_BOT_PWD`
- README : installation en trois commandes sur machine vierge, lien vers ce
  document, captures des `curl` de validation des trois accès
- Création du doc Grist (tables `veilles` et `resultats` conformes aux
  contrats, `objectif` comprise) et du salon Tchap de diffusion, le compte
  bot y étant invité
- Spike : interroger `parlement.tricoteuses.fr/v2/amendements` sur un jour
  réel — pagination, champs présents/absents, valeurs réelles de `sort`,
  latence — consigner dans `docs/api-tricoteuses.md`
- `DECISIONS.md` initialisé avec les décisions actées ci-dessous

Besoins : clés Albert, Grist, compte bot Tchap (voir décision "notification").
Une clé par équipe, stockée dans un canal privé, jamais dans le dépôt.

### B1 — Recherche et écriture Grist · DEV ou DATA · dépend de B0

- `fetch_api.py` (déjà écrit) : un appel par veille active, sur la
  ressource `source`, avec `liste` en mots-clés de recherche et la plage
  de la journée traitée — voir `docs/api-tricoteuses.md`
- Filtrage local unique restant : un terme d'`exclusion` présent dans le
  texte (exposé + dispositif, ou champ pertinent de la ressource) annule
  le résultat
- Extrait de citation : phrase du texte contenant le terme recherché
  (fonction utilitaire courte, pas un moteur de matching à maintenir)
- `grist.py` : lecture de `veilles`, écriture des **nouvelles** lignes de
  `resultats` par lots via l'API REST
  (`POST /api/docs/{doc}/tables/{table}/records`) — voir
  `docs/api-grist.md`
- Idempotence : jamais de réinsertion d'une paire (uid, veille)
  existante — c'est ce qui rend tout le pipeline relançable sans
  précaution
- Un test du filtrage par exclusion, un test du diff d'idempotence

Ce bloc remplace les anciens blocs d'acquisition, de nettoyage et de
matching (lexical, métadonnées, sémantique) : l'API Tricoteuses fait déjà
la recherche server-side avec filtre de date, il n'y a plus de pipeline
local à écrire ni à maintenir pour ça. Le suivi du sort d'un `uid` déjà en
base est traité à part, voir B1.5.

Outils : `veille.fetch_api`, requests sur l'API Grist. Pas de classe, pas
de client tiers.

### B1.5 — Suivi du sort · DATA ou débutant encadré · dépend de B1

- `grist.maj_sorts` : à chaque run, comparer le `sort` renvoyé par l'API
  pour les `uid` déjà présents dans `resultats` avec celui stocké ; s'il a
  changé, mettre à jour la ligne et renseigner `evolution` — voir
  `docs/api-grist.md` (PATCH sur `resultats`)
- Isolé de B1 pour que les deux tâches se prennent et se testent en
  parallèle : B1 ne fait qu'insérer du neuf, B1.5 ne fait que réconcilier
  l'existant
- Un test dédié du changement de sort

Outils : requests sur l'API Grist, pas de client tiers.

### B2 — Design de la synthèse · MÉTIER (+ DEV/DATA en relecture) · aucune dépendance, démarre dès J1 matin

Bloc de réflexion, aucun code. Produit un document écrit
(`docs/synthese-design.md`, à créer) qui devient le contrat d'entrée de
B4 : B4 implémente strictement ce que B2 a spécifié, il n'invente pas la
structure du prompt.

- Structure attendue du paragraphe de synthèse : longueur (3 à 5 phrases),
  ton, ordre des idées
- Usage du champ `objectif` de chaque veille : comment il oriente le
  contenu de la synthèse au-delà d'un simple résumé des extraits
- La synthèse doit-elle mentionner les évolutions de sort, ou se limiter
  aux nouveaux résultats du jour ?
- Cas déluge (PLF) : la synthèse annonce un volume plutôt que de tenter un
  résumé exhaustif de centaines de documents
- Un exemple annoté bout en bout : extraits + objectif en entrée →
  paragraphe de synthèse attendu en sortie

Le format du reste du digest (top 5 par veille au format "titre + deux
lignes + lien", section évolutions, lien vue Grist) est déjà acté et
n'est pas un sujet de réflexion ouvert pour ce bloc — B5 l'implémente
directement.

### B3 — Configuration et vues Grist · MÉTIER · aucun code, aucune dépendance

- Rédiger les veilles réelles de démonstration : mots-clés avec leurs
  variantes et exclusions, sujets en français, chacune avec un `objectif`
  en une phrase, en mobilisant la connaissance de l'Assemblée (vocabulaire
  des exposés des motifs, intitulés des programmes budgétaires, noms
  usuels des commissions)
- Construire les vues Grist selon deux mécanismes distincts (voir
  `docs/dashboards.md`) : des **chart widgets** pour les indicateurs
  d'agrégat (volumes par jour, répartition par source, taux de
  pertinence) et des **linked widgets** pour la navigation (résultats
  filtrés par veille sélectionnée, par texte, par auteur)
- Qualifier les résultats via la colonne `pertinent` — ce travail est le
  contrôle qualité qui sert à ajuster les veilles (mots-clés, exclusions,
  objectif)

Ce bloc démarre dès J1 matin, sans attendre le moindre code.

### B4 — Génération de la synthèse par Albert · DEV ou DATA · dépend de B1, B1.5, B2 et B3

Remplace l'ancien bloc d'évaluation et calibration : l'usage d'Albert
n'est plus la recherche sémantique (déléguée à Tricoteuses), c'est la
génération en langage naturel d'un paragraphe de synthèse — et rien
d'autre : ce bloc ne publie pas, ne connaît pas Tchap.

- Implémente strictement le gabarit défini par B2 : un appel
  `POST /v1/chat/completions` (Mistral-Small-3.2-24B) qui reçoit, par
  veille, l'`objectif` (B3) et les `extrait`/`evolution` du jour
  (B1/B1.5), et renvoie un paragraphe de synthèse en français — voir
  `docs/api-albert.md`
- Le prompt ne fournit que les `extrait` déjà en base, jamais le document
  complet : la synthèse ne peut pas introduire un fait hors des citations
  déjà sourcées
- Sortie : une chaîne de caractères, transmise à B5. Ce bloc ne l'ajoute
  pas lui-même au digest ni ne l'envoie
- Quotas Albert (offre Expérimentation, vérifiés via `GET /v1/me/info`) :
  chat 50 req/min et 1 000 req/jour — un seul appel de synthèse par run,
  largement dans les clous
- Bascule si Albert est indisponible : renvoyer une chaîne vide plutôt que
  d'échouer — B5 gère l'absence de synthèse dans le digest

Besoins : clé Albert testée à J0, spec de B2 disponible.

### B5 — Publication du digest sur Tchap · MÉTIER + étudiant · dépend de B4 et B1/B1.5

- Étudiant, `digest.py` : le paragraphe de synthèse de B4 ouvre le
  digest ; puis, par veille, top 5 trié par `date_depot` au format "titre +
  deux lignes + lien" (lisible en 30 secondes) ; une section "évolutions"
  listant les sorts changés (B1.5) ; un lien par veille vers la vue Grist
  filtrée pour le reste ; envoi par la fonction send-only Tchap
  (`send_markdown_message`, le markdown est rendu nativement) —
  voir `docs/api-tchap-maubot.md`
- En période de déluge (PLF), le digest annonce le volume et montre le
  top : "212 amendements sur ‹fiscalité verte›, top 5 ci-dessous, le reste
  dans Grist" — le digest montre le top et annonce le volume, la liste
  complète vit dans Grist, où elle est triable
- Si B4 renvoie une chaîne vide (Albert indisponible ou quota atteint), le
  digest part quand même, sans le paragraphe de tête : les extraits
  sourcés suffisent à eux seuls
- MÉTIER : rédiger le gabarit markdown (à partir de la spec B2 pour la
  partie synthèse), arbitrer ce qui mérite le digest, tester la
  lisibilité sur mobile (Tchap est d'abord utilisé sur téléphone)

### B6 — Orchestration · DEV · dépend de tout, volontairement trivial

- `run.py` : `veilles (Grist) → recherche + écriture (B1) → suivi du sort
  (B1.5) → génération de la synthèse (B4) → publication (B5)`, option
  `--date`, relançable sans doublons (garanti par B1), code de sortie non
  nul si une étape critique échoue
- Le pipeline est une suite d'appels de fonctions dans un seul fichier ;
  l'automatisation = ce fichier dans un ordonnanceur externe (CronJob du
  catalogue Onyxia ou schedule GitHub Actions), sans une ligne à réécrire
- Le cron se pose dans la dernière heure du hackathon, seulement si la démo
  est validée

### B7 — Extensions · à ouvrir seulement si B0-B6 tiennent

1. **Extension à d'autres corpus Tricoteuses.** Le pipeline B1/B1.5 est
   déjà générique sur le paramètre `source` : toute ressource Tricoteuses
   avec un champ de date devient une veille possible sans nouveau code.
   Par ordre de rentabilité : Questions au Gouvernement (écrites, orales,
   texte riche, excellent rapport signal/effort) ; Agenda des réunions
   (veille d'anticipation, "votre sujet passe en commission demain") ;
   Sénat (ressources `senat-*` de l'écosystème Tricoteuses) ; Comptes
   rendus (le plus riche mais hors schéma, flux Syceron, parsing ad hoc —
   dernier de la liste).
2. **Mode RAG sur les résultats accumulés.** Réutilise les briques
   d'ingestion/recherche Albert archivées (`src/archive/match_semantique.py`,
   documentées dans `docs/api-albert.md`) dans un but différent :
   interroger l'historique cumulé de `resultats`/`extrait`, pas détecter
   le jour même.
3. **Mode conversationnel sur ce RAG.** Une boucle question/réponse
   au-dessus de l'index du point 2, bornée aux extraits déjà sourcés —
   même principe d'explicabilité que B4 : pas de fait hors du corpus
   accumulé.
4. **Extension maubot.** Expose le mode conversationnel du point 3 dans le
   salon Tchap ; réutilise le compte bot de B5, cette fois avec un plugin
   qui écoute (B5 reste volontairement send-only).
5. **Widget Grist sur mesure.** Un widget custom, si le temps le permet ;
   déroge explicitement à la décision "no-code renforcé" du cœur du
   projet — assumé comme extension seulement, jamais requis pour la démo.

## Ordre de marche

Calé sur le programme officiel (~8 h de code vendredi, ~4 h samedi,
gel à 14h, restitution de 3 minutes à 16h) — détail dans
docs/organisation.md :

- **Avant vendredi 14h** : B0 (dont le spike API amendements), compte bot
  Tchap demandé.
- **Vendredi 14h-19h** : B1, B1.5, B3 et B2 (design) en parallèle — B2 ne
  dépend de rien, il démarre immédiatement. Jalon du dîner : run partiel
  recherche Tricoteuses → Grist (B1) depuis main.
- **Vendredi soir** : B4 (génération, une fois B2 et B3 avancés) puis B5
  (publication). Jalon 22h30 : le premier digest complet, synthèse
  comprise, tombe dans le salon Tchap.
- **Samedi 9h45-13h30** : polissage B4/B5, B6 (orchestration) ; gel
  interne 13h30, puis script de restitution et deux répétitions.
- B7 pour les mains libres uniquement, sans toucher à main.

À 3 personnes : DEV = B0 + B4 + B6, DATA = B1 + B1.5, MÉTIER = B2 + B3 + B5.
À 12 : un bloc par personne, étudiants en binôme sur B1/B1.5 et B5.

## Décisions actées — on en reparle volontiers, après la restitution

Chaque réouverture en cours de route coûte une synchro à douze.

- **Source et recherche** : API REST Tricoteuses
  (`parlement.tricoteuses.fr/v2`) — filtre de date et recherche
  plein texte côté serveur. Elle remplace l'acquisition locale (clone Git,
  dump officiel) et le matching local (lexical, métadonnées, sémantique) :
  un appel par veille suffit. Le dump officiel et le clone Git restent des
  solutions de repli documentées mais ne sont plus le chemin principal.
  Pas de flux temps réel : notre promesse est J+1, pas le temps réel.
- **Push, pas pull** : la veille est un balayage exhaustif push avec
  garantie de rappel. Un usage conversationnel (pull, best-effort) reste
  un complément explicitement secondaire, hors du chemin critique du
  hackathon — voir B7.2-B7.4, qui s'appuient sur un RAG construit en
  interne sur nos propres résultats accumulés, pas sur un service tiers.
- **Stockage** : Grist est le front utilisateur (config, résultats,
  historique, vues) ; l'API Tricoteuses est la donnée, ré-interrogeable à
  tout instant ; pas de cache disque nécessaire côté acquisition. Besoin
  futur de stockage intermédiaire → Parquet sur le S3 d'Onyxia (décision
  différée, défaut nommé).
- **Matching** : délégué à la recherche server-side de l'API Tricoteuses
  pour les quatre types de veille (`mot_cle`, `sujet`, `parlementaire`,
  `dossier`) ; seul le filtrage par `exclusion` reste local. Albert n'est
  plus utilisé pour la recherche/l'appariement, uniquement pour la
  génération de la synthèse du digest (B4) — décision qui remplace
  l'ancienne répartition lexical/métadonnées/sémantique.
- **Synthèse pilotée par objectif** : chaque veille porte un `objectif` en
  français (table `veilles`), fourni tel quel dans le prompt de B4. La
  synthèse n'est pas un résumé générique des extraits, elle répond à
  l'intention déclarée par MÉTIER. Le design de ce qu'elle doit contenir
  (B2) est séparé de son implémentation (B4) et de sa publication (B5)
  pour que les trois puissent avancer sans se bloquer mutuellement.
- **Notification** : compte Tchap dédié (adossé à une BALF, procédure
  documentée par la communauté Tchap et le retour d'expérience SSPhub) piloté
  par `simplematrixbotlib`. Pour le digest (B5), pas de bot qui écoute :
  une fonction send-only appelée en fin de run.py, qui ne demande rien à
  héberger ; maubot viendra avec le bot interactif (B7.4), qui réutilisera
  le même compte. Fallback si le compte n'arrive pas à temps : digest par
  mail, l'envoi étant isolé derrière une fonction unique.
- **No-code renforcé** : les colonnes calculées Grist (formules Python dans
  Grist) sont le territoire de MÉTIER — liens construits depuis l'uid,
  compteurs — sans toucher au dépôt. Pas de widget custom dans le cœur du
  projet : les chart widgets et linked widgets standard suffisent (voir
  `docs/dashboards.md`) ; un widget sur mesure reste une extension
  possible (B7.5), jamais requis pour la démo.
- **Orchestration** : `run.py` manuel pendant le hackathon, cron externe
  ensuite. Pas de n8n, pas de scheduler maison, pas de framework.
- **Hors scope assumé** face aux offres privées : temps réel < 30 min,
  presse et audiovisuel, transcription vidéo, cartographie des décideurs.
  Notre périmètre : ciblage (mot-clé, sujet, parlementaire, dossier),
  digest sourcé et synthétisé selon l'objectif déclaré, suivi du sort —
  entièrement sur briques de l'État.
