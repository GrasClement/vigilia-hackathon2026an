# Veille parlementaire — Architecture et découpage en blocs

Version révisée : l'acquisition et le matching (mots-clés, métadonnées,
sémantique) sont délégués à la recherche server-side de l'API Tricoteuses ;
Albert n'est plus un moteur de recherche mais l'outil de synthèse du
digest. Ce document est la référence du dépôt : tout nouveau contributeur
le lit avant d'écrire une ligne de code. Il définit les contrats
d'interface, les blocs de travail (tâches, outils, besoins, profil requis,
dépendances) et les décisions d'architecture actées.

## Le projet en trois phrases

Chaque administration, chercheur ou citoyen décrit ses sujets d'intérêt dans
un tableau Grist — mot-clé, sujet en français, parlementaire ou dossier — et
reçoit chaque matin sur Tchap un digest sourcé des travaux de l'Assemblée qui
le concernent, avec l'extrait qui justifie chaque alerte et un paragraphe de
synthèse généré par Albert. Le système suit également le devenir des
documents détectés (amendement adopté, rejeté). Tout repose sur l'open data
de l'Assemblée via l'API Tricoteuses et les briques souveraines de l'État :
Grist, Albert API, Tchap (via maubot), hébergement Onyxia.

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
  l'écriture Grist, le filtrage par exclusion, la synthèse Albert.
- `MÉTIER` : connaissance de l'Assemblée et de ses textes, pas de code.
  Prend la configuration Grist, la qualification des résultats, le contenu
  du digest. Ce profil porte la démonstration "no code" : tout ce qu'il fait
  doit être faisable par un futur utilisateur sans développeur.

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

### Table Grist `veilles` — éditée par MÉTIER, lue par B1

```
id | type | liste | actif | source | exclusion
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

### Table Grist `resultats` — écrite par B1, lue par B2, B4 et les vues

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
- `evolution` : renseignée quand le `sort` change après détection
  ("adopté le JJ/MM"). C'est le suivi du devenir, alimenté gratuitement
  par le rappel quotidien de l'API sur les mêmes `uid`.
- `pertinent` : oui/non/vide, rempli à la main par MÉTIER. C'est la
  vérité terrain utilisée pour ajuster les veilles (mots-clés, exclusions).
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
  contrats) et du salon Tchap de diffusion, le compte bot y étant invité
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
- `grist.py` : lecture de `veilles`, écriture de `resultats` par lots via
  l'API REST (`POST /api/docs/{doc}/tables/{table}/records`) —
  voir `docs/api-grist.md`
- Idempotence : jamais de réinsertion d'une paire (uid, veille)
  existante — c'est ce qui rend tout le pipeline relançable sans
  précaution
- Suivi du sort : à chaque run, comparer le `sort` renvoyé par l'API avec
  celui des `uid` déjà en base ; s'il a changé, mettre à jour la ligne et
  renseigner `evolution`
- Un test du filtrage par exclusion, un test du diff d'idempotence, un
  test du changement de sort

Ce bloc remplace les anciens blocs d'acquisition, de nettoyage et de
matching (lexical, métadonnées, sémantique) : l'API Tricoteuses fait déjà
la recherche server-side avec filtre de date, il n'y a plus de pipeline
local à écrire ni à maintenir pour ça.

Outils : `veille.fetch_api`, requests sur l'API Grist. Pas de classe, pas
de client tiers.

### B2 — Digest Tchap · MÉTIER + étudiant · dépend de B1 et B4

- Étudiant, `digest.py` : le paragraphe de synthèse d'Albert (B4) ouvre le
  digest ; puis, par veille, top 5 trié par `date_depot` au format "titre +
  deux lignes + lien" (lisible en 30 secondes) ; une section "évolutions"
  listant les sorts changés ; un lien par veille vers la vue Grist filtrée
  pour le reste ; envoi par la fonction send-only Tchap
  (`send_markdown_message`, le markdown est rendu nativement) —
  voir `docs/api-tchap-maubot.md`
- En période de déluge (PLF), le digest annonce le volume et montre le
  top : "212 amendements sur ‹fiscalité verte›, top 5 ci-dessous, le reste
  dans Grist" — le digest montre le top et annonce le volume, la liste
  complète vit dans Grist, où elle est triable
- Si la synthèse Albert n'est pas disponible (bloc B4 en panne ou quota
  atteint), le digest part quand même, sans le paragraphe de tête : les
  extraits sourcés suffisent à eux seuls
- MÉTIER : rédiger le gabarit markdown, arbitrer ce qui mérite le digest,
  tester la lisibilité sur mobile (Tchap est d'abord utilisé sur téléphone)

### B3 — Configuration et vues Grist · MÉTIER · aucun code, aucune dépendance

- Rédiger les veilles réelles de démonstration : mots-clés avec leurs
  variantes et exclusions, sujets en français, en mobilisant la
  connaissance de l'Assemblée (vocabulaire des exposés des motifs,
  intitulés des programmes budgétaires, noms usuels des commissions)
- Construire les vues Grist : résultats par veille, par texte, par auteur ;
  tableau de bord simple (volumes par jour, répartition par source) —
  voir `docs/dashboards.md`
- Qualifier les résultats via la colonne `pertinent` — ce travail est le
  contrôle qualité qui sert à ajuster les veilles (mots-clés, exclusions)

Ce bloc démarre dès J1 matin, sans attendre le moindre code.

### B4 — Synthèse par Albert API · DEV ou DATA · dépend de B1 et B3

Remplace l'ancien bloc d'évaluation et calibration : l'usage d'Albert
n'est plus la recherche sémantique (déléguée à Tricoteuses), c'est la
synthèse en langage naturel du digest.

- À chaque run, un appel `POST /v1/chat/completions` (Mistral-Small-3.2-24B)
  reçoit les lignes de `resultats` du jour, regroupées par veille, et
  produit un paragraphe de synthèse en français (3 à 5 phrases) — voir
  `docs/api-albert.md`
- Le prompt ne fournit que les `extrait` déjà en base, jamais le document
  complet : la synthèse ne peut pas introduire un fait hors des citations
  déjà sourcées
- Le paragraphe s'ajoute en tête du digest (B2), il ne remplace jamais les
  extraits cités individuellement — l'explicabilité native reste la règle
- Quotas Albert (offre Expérimentation, vérifiés via `GET /v1/me/info`) :
  chat 50 req/min et 1 000 req/jour — un seul appel de synthèse par run,
  largement dans les clous
- Bascule si Albert est indisponible : digest envoyé sans synthèse (voir
  B2 et les Plans B de `docs/organisation.md`)

Besoins : clé Albert testée à J0.

### B5 — Orchestration · DEV · dépend de tout, volontairement trivial

- `run.py` : `veilles (Grist) → recherche + écriture (B1) → synthèse
  Albert (B4) → digest (B2)`, option `--date`, relançable sans doublons
  (garanti par B1), code de sortie non nul si une étape critique échoue
- Le pipeline est une suite d'appels de fonctions dans un seul fichier ;
  l'automatisation = ce fichier dans un ordonnanceur externe (CronJob du
  catalogue Onyxia ou schedule GitHub Actions), sans une ligne à réécrire
- Le cron se pose dans la dernière heure du hackathon, seulement si la démo
  est validée

### B6 — Extensions · à ouvrir seulement si B1-B5 tiennent

Par ordre de rentabilité :

1. **Questions au Gouvernement** (écrites, orales) : même bloc B1, autre
   `source` Tricoteuses (`questions`), veilles dédiées — MÉTIER identifie
   les champs utiles, un étudiant vérifie le mapping. Texte riche,
   excellent rapport signal/effort.
2. **Agenda des réunions** : veille d'anticipation ("votre sujet passe en
   commission demain"), `source` = `reunions`, digest séparé.
3. **Agent de consultation** : un plugin maubot interactif qui répond aux
   questions de suivi dans le salon ("où en est ce texte ? qui est
   l'auteur ?") via le serveur MCP Parlement de Tricoteuses. Complément
   pull du produit push, jamais son remplacement.
4. **Sénat** : ressources `senat-*` de l'écosystème Tricoteuses, même
   bloc B1, nouvelles `source`.
5. **Comptes rendus** : le plus riche mais hors schéma (flux Syceron),
   parsing ad hoc garanti. Dernier de la liste.

## Ordre de marche

Calé sur le programme officiel (~8 h de code vendredi, ~4 h samedi,
gel à 14h, restitution de 3 minutes à 16h) — détail dans
docs/organisation.md :

- **Avant vendredi 14h** : B0, compte bot Tchap demandé.
- **Vendredi 14h-19h** : B1 et B3 en parallèle. Jalon du dîner : run
  partiel recherche Tricoteuses → Grist depuis main.
- **Vendredi soir** : B4 et B2. Jalon 22h30 : le premier digest, synthèse
  Albert comprise, tombe dans le salon Tchap.
- **Samedi 9h45-13h30** : polissage B2/B4, B5 ; gel interne 13h30, puis
  script de restitution et deux répétitions.
- B6 pour les mains libres uniquement, sans toucher à main.

À 3 personnes : DEV = B0 + B4 + B5, DATA = B1, MÉTIER = B3 + B2.
À 12 : un bloc par personne, étudiants en binôme sur B1 et B2.

## Décisions actées — on en reparle volontiers, après la restitution

Chaque réouverture en cours de route coûte une synchro à douze.

- **Source et recherche** : API REST Tricoteuses
  (`parlement.tricoteuses.fr/v2`) — filtre de date et recherche
  plein texte côté serveur. Elle remplace l'acquisition locale (clone Git,
  dump officiel) et le matching local (lexical, métadonnées, sémantique) :
  un appel par veille suffit. Le dump officiel et le clone Git restent des
  solutions de repli documentées mais ne sont plus le chemin principal.
  Pas de flux temps réel : notre promesse est J+1, pas le temps réel.
- **MCP** : pas le produit. La veille est un balayage exhaustif push avec
  garantie de rappel ; un MCP est du pull best-effort pour agent
  conversationnel. Réutilisé en B6.3 comme complément de consultation.
- **Stockage** : Grist est le front utilisateur (config, résultats,
  historique, vues) ; l'API Tricoteuses est la donnée, ré-interrogeable à
  tout instant ; pas de cache disque nécessaire côté acquisition. Besoin
  futur de stockage intermédiaire → Parquet sur le S3 d'Onyxia (décision
  différée, défaut nommé).
- **Matching** : délégué à la recherche server-side de l'API Tricoteuses
  pour les quatre types de veille (`mot_cle`, `sujet`, `parlementaire`,
  `dossier`) ; seul le filtrage par `exclusion` reste local. Albert n'est
  plus utilisé pour la recherche/l'appariement, uniquement pour la
  synthèse du digest (B4) — décision qui remplace l'ancienne répartition
  lexical/métadonnées/sémantique.
- **Notification** : compte Tchap dédié (adossé à une BALF, procédure
  documentée par la communauté Tchap et le retour d'expérience SSPhub) piloté
  par `simplematrixbotlib`. Pour le digest, pas de bot qui écoute : une
  fonction send-only appelée en fin de run.py, qui ne demande rien à
  héberger ; maubot viendra avec le bot interactif (B6.3), qui réutilisera
  le même compte. Fallback si le compte n'arrive pas à temps : digest par
  mail, l'envoi étant isolé derrière une fonction unique.
- **No-code renforcé** : les colonnes calculées Grist (formules Python dans
  Grist) sont le territoire de MÉTIER — liens construits depuis l'uid,
  compteurs — sans toucher au dépôt. Pas de widget custom : les vues
  standard suffisent.
- **Orchestration** : `run.py` manuel pendant le hackathon, cron externe
  ensuite. Pas de n8n, pas de scheduler maison, pas de framework.
- **Hors scope assumé** face aux offres privées : temps réel < 30 min,
  presse et audiovisuel, transcription vidéo, cartographie des décideurs.
  Notre périmètre : ciblage (mot-clé, sujet, parlementaire, dossier),
  digest sourcé et synthétisé, suivi du sort — entièrement sur briques de
  l'État.
