# Veille parlementaire — Architecture et découpage en blocs

Version finale. Ce document est la référence du dépôt GitLab : tout nouveau
contributeur le lit avant d'écrire une ligne de code. Il définit les contrats
d'interface, les dix blocs de travail (tâches, outils, besoins, profil requis,
dépendances) et les décisions d'architecture actées.

## Le projet en trois phrases

Chaque administration, chercheur ou citoyen décrit ses sujets d'intérêt dans
un tableau Grist — mot-clé, thème en français, parlementaire ou dossier — et
reçoit chaque matin sur Tchap un digest sourcé des travaux de l'Assemblée qui
le concernent, avec l'extrait qui justifie chaque alerte. Le système suit
également le devenir des documents détectés (amendement adopté, rejeté). Tout
repose sur l'open data de l'Assemblée et les briques souveraines de l'État :
Grist, Albert API, Tchap (via maubot), hébergement Onyxia.

## Profils de contributeurs

- `DEV` : Python confirmé. Prend les blocs qui touchent aux API externes et
  à l'assemblage.
- `DATA` : à l'aise en notebook, code débutant à intermédiaire. Prend le
  nettoyage, le matching lexical, l'évaluation.
- `MÉTIER` : connaissance de l'Assemblée et de ses textes, pas de code.
  Prend la configuration Grist, la qualification des résultats, le contenu
  du digest. Ce profil porte la démonstration "no code" : tout ce qu'il fait
  doit être faisable par un futur utilisateur sans développeur.

## Contrats d'interface

Ces trois structures sont l'épine dorsale du projet. Un bloc peut être réécrit
entièrement sans toucher aux autres tant qu'il respecte son contrat. Toute
modification d'un contrat se décide en synchro d'équipe et se consigne dans
DECISIONS.md — jamais dans un commit isolé.

### Document propre — sortie de B2, entrée de B3 et B4

```python
{"uid": str,          # identifiant AN, ex. AMANR5L17PO838901B1906P1D1N001548
 "numero": str,        # numéro d'amendement lisible
 "auteur": str,        # nom complet de l'auteur principal
 "texte_ref": str,     # référence du texte législatif visé
 "date_depot": str,    # ISO YYYY-MM-DD
 "place": str,         # division visée, ex. "Article 2 bis"
 "sort": str,          # sort si voté, sinon état ("En traitement")
 "url": str,           # assemblee-nationale.fr/dyn/{leg}/amendements/{uid}
 "expose": str,        # exposé des motifs, texte nettoyé UTF-8
 "dispositif": str}    # dispositif, texte nettoyé UTF-8
```

### Table Grist `veilles` — éditée par MÉTIER, lue par B3 et B4

```
libelle | type | expression | exclusions | actif
```

Quatre valeurs de `type` :

- `mot_cle` : matching lexical exact, insensible à la casse. Garantie de
  rappel : le terme présent déclenche toujours.
- `theme` : description en français, appariée sémantiquement via Albert.
- `parlementaire` : filtre sur le champ auteur. Pas d'IA, égalité souple.
- `dossier` : filtre sur texte_ref. Idem.

`exclusions` (optionnel) : termes qui annulent un match lexical — le levier
anti-bruit standard du domaine. `actif` permet de suspendre une veille sans
la supprimer.

### Table Grist `resultats` — écrite par B5, lue par B6 et les vues

```
uid | veille | score | extrait | methode | evolution |
texte_ref | auteur | date_depot | sort | url | pertinent
```

- Une ligne par paire document × veille ; un amendement touchant deux veilles
  produit deux lignes, chacune avec son extrait. C'est voulu.
- `score` 0-100 : 100 pour un match lexical ou métadonnées ; score de
  `/v1/search` renormalisé pour un thème. Pas de formule composite maison.
- `extrait` : la justification, toujours citée depuis le document — phrase
  contenant le terme (lexical), chunk retourné par Albert (thème), champ
  matché (métadonnées). L'explicabilité est native, jamais générée seule ;
  au niveau 2+, le motif rédigé par le LLM juge s'ajoute à l'extrait, il ne
  le remplace jamais.
- `methode` : lexical | metadonnees | semantique.
- `evolution` : renseignée quand le `sort` change après détection ("adopté
  le JJ/MM"). C'est le suivi du devenir, alimenté gratuitement par le
  re-téléchargement quotidien du dump complet.
- `pertinent` : oui/non/vide, rempli à la main par MÉTIER. C'est la vérité
  terrain de l'évaluation (B8).
- Hiérarchisation : tri par score dans le digest et les vues, jamais de
  filtre binaire. Le seuil ne sert qu'à couper la queue (top-k par veille,
  de toute façon imposé par les quotas Albert).

## Blocs de travail

Une issue GitLab par bloc ; les tâches ci-dessous en sont la checklist.
Branches `feature/<bloc>-<sujet>`, MR vers main, merge par l'intégrateur.

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

### B1 — Acquisition · DATA ou étudiant débutant · dépend de B0 et du spike J0

Option A retenue (validée sur les fichiers réels : JSON éclatés, un fichier
par amendement, champs riches et lisibles) ; l'option B reste codée en fallback.

**Option A — dépôts Git Tricoteuses.** Données AN converties en
JSON, nettoyées et versionnées par la communauté, mises à jour plusieurs fois
par jour ; ressource officiellement recommandée du hackathon. L'acquisition
devient `git pull`, et le "quoi de neuf" devient `git diff --name-only` :
l'incrémental et l'idempotence sont fournis par git lui-même, et B2 fond
presque entièrement. Reste à vérifier au spike J0 : taille du clone et
fraîcheur effective ; le contenu, lui, est validé.

**Option B, fallback garanti — dump officiel quotidien.** URL vérifiée pour
la 17e législature :
`https://data.assemblee-nationale.fr/static/openData/repository/17/loi/amendements_div_legis/Amendements.json.zip`
(latence annoncée : 1 jour ; vérifier la fraîcheur réelle au spike). La
fonction tient en dix lignes : GET, unzip en mémoire, parse des JSON. Cache
disque dans `data/` pour ne pas re-télécharger dans la journée.

Dans les deux cas la sortie alimente B2 (ou directement le contrat "document
propre" si Tricoteuses livre déjà propre) : la source est un module swappable
et l'option B reste codée en secours, activable par une variable d'env.

Outils : git, ou requests + zipfile + json (stdlib). Pas de classe, pas de
retry, pas de proxy.

### B2 — Nettoyage et extraction · DATA · dépend de B1

- `clean.py` : `strip_html` (html.unescape + regex, le HTML des corps est
  simple et bien formé) et `extract_amendement`, le mapping JSON Tricoteuses
  → contrat "document propre". Les deux fonctions sont déjà écrites (issue
  du bloc), le travail du bloc est de les valider sur un échantillon large
- Chemins connus : uid, identification.numeroLong, signataires.libelle
  (noms lisibles, cosignataires inclus — pas de référentiel acteurs à
  résoudre), texteLegislatifRef, pointeurFragmentTexte.division.titre,
  cycleDeVie.dateDepot, corps.contenuAuteur.{exposeSommaire, dispositif}
- À vérifier sur le dépôt, pas à coder préventivement : chemin du sort une
  fois l'amendement voté (les exemples frais sont "En traitement") ;
  dispositif structuré des amendements de crédits (fallback fragmenthtml
  officiel, à coder seulement si le cas apparaît) ; exposé absent sur les
  amendements de suppression (géré)
- Limitation acceptée : les rectifications (numeroRect > 0, même uid) ne
  sont pas re-matchées ; `chronotag` permettra de le faire plus tard
- Un test sur deux JSON réels commités dans `tests/data/`

Outils : html et re (stdlib), rien d'autre.

### B3 — Matching lexical et métadonnées · DATA · dépend de B2

- `match_lexical.py` : pour chaque veille `mot_cle`, recherche insensible à
  la casse et aux entités résiduelles dans exposé + dispositif ; extrait = la
  phrase contenant le terme ; tout terme d'`exclusions` présent annule le
  match
- `match_meta.py` : veilles `parlementaire` et `dossier`, égalité souple
  (casse, espaces) sur auteur / texte_ref ; extrait = le champ matché
- Un test couvrant : accents, casse, entité résiduelle, exclusion qui annule

Outils : Python pur. Pas de rapidfuzz, pas de regex au-delà du découpage en
phrases : la valeur de ce bloc est sa prévisibilité.

### B4 — Matching sémantique · DEV · dépend de B2

- `match_semantique.py` : une collection Albert par run, nommée par
  paramètre (date ou label — le backfill de B8 en a besoin ; la purge des
  anciennes est reportée après le hackathon) ; le scope de recherche est
  le bon par construction, aucun filtre à écrire ; `POST /v1/documents` un document
  par amendement nouveau avec `disable_chunking=true` : un amendement = un
  chunk = un extrait exactement traçable ; texte = exposé + dispositif
  tronqué à ~8 000 caractères, sans en-tête artificiel ; metadata =
  {"uid", "texte_ref", "date_depot"} pour rejoindre la ligne de résultat
- Pour chaque veille `theme` active : `POST /v1/search`, `method=hybrid`
  (fusion sémantique + lexicale incluse), limité au top-k. Pas de reranker
  explicite : B8 dira s'il apporte quelque chose
- Score renormalisé en 0-100 ; extrait = le chunk, entier dans Grist,
  tronqué à ~300 caractères dans le digest
- Quotas Albert (offre Expérimentation, vérifiés) : embeddings bge-m3
  500 req/min et 50 000 req/jour, chat Mistral-Small-3.2-24B 50 req/min et
  1 000 req/jour, reranker disponible. Conséquences : l'ingestion tient même
  un pic PLF en espaçant les requêtes ; le LLM juge (niveau 2+) est réservé
  au top-k. Les limites exactes du compte se lisent dans `GET /v1/me/info`
- Niveau 2+ : LLM juge sur le top-k, produisant un motif d'une phrase ajouté
  à l'extrait

Besoins : clé Albert testée à J0 sur les volumes réels.

### B5 — Écriture Grist · étudiant débutant · dépend des contrats

- `grist.py` : lecture de `veilles`, écriture de `resultats` par lots via
  l'API REST (`POST /api/docs/{doc}/tables/{table}/records`)
- Idempotence : jamais de réinsertion d'une paire (uid, veille) existante —
  c'est ce qui rend tout le pipeline relançable sans précaution
- Suivi du sort : à chaque run, comparer le `sort` du dump avec celui des
  uid déjà en base ; s'il a changé, mettre à jour la ligne et renseigner
  `evolution`
- Un test du diff d'idempotence et un test du changement de sort

Outils : requests sur l'API Grist, pas de client tiers.

### B6 — Digest Tchap · MÉTIER + étudiant · dépend de B5

- Étudiant, `digest.py` : agréger les résultats du jour par texte législatif ;
  par veille, top 5 trié par score au format "titre + deux lignes + lien"
  (lisible en 30 secondes) ; une section "évolutions" listant les sorts
  changés ; un lien par veille vers la vue Grist filtrée pour le reste ;
  envoi par la fonction send-only Tchap (`send_markdown_message`, le
  markdown est rendu nativement)
- En période de déluge (PLF), le digest annonce le volume et montre le top :
  "212 amendements sur ‹fiscalité verte›, top 5 ci-dessous, le reste dans
  Grist" — le digest montre le top et annonce le volume, la liste
  complète vit dans Grist, où elle est triable
- MÉTIER : rédiger le gabarit markdown, arbitrer ce qui mérite le digest,
  tester la lisibilité sur mobile (Tchap est d'abord utilisé sur téléphone)

### B7 — Configuration et vues Grist · MÉTIER · aucun code, aucune dépendance

- Rédiger les veilles réelles de démonstration : mots-clés avec leurs
  variantes et exclusions, thèmes en français, en mobilisant la connaissance
  de l'Assemblée (vocabulaire des exposés des motifs, intitulés des
  programmes budgétaires, noms usuels des commissions)
- Construire les vues Grist : résultats par veille, par texte, par auteur ;
  tableau de bord simple (volumes par jour, répartition par méthode)
- Qualifier les résultats via la colonne `pertinent` — ce travail est à la
  fois le contrôle qualité et le jeu d'évaluation de B8

Ce bloc démarre dès J1 matin, sans attendre le moindre code.

### B8 — Évaluation et calibration · DATA · dépend de B1-B4 et de B7

- Backfill ciblé, calendrier oblige : un dossier législatif riche ou un
  mois de dépôts, pas la législature — l'objectif est un chiffre pour le
  pitch, pas une étude
- Mesurer précision et rappel par méthode sur les veilles qualifiées ;
  calibrer le top-k et le seuil de coupe
- Produire les deux chiffres du pitch : "sur N mois, X documents détectés
  sur [veille de démo], dont Y sans mention littérale du terme" — Y est ce
  que le lexical seul rate, donc la justification chiffrée d'Albert

Notebook `#%%` dans `notebooks/`, conclusions en markdown dans le dépôt.

### B9 — Orchestration · DEV · dépend de tout, volontairement trivial

- `run.py` : `fetch → clean → match_lexical + match_meta + match_semantique
  → grist → digest`, option `--date`, relançable sans doublons (garanti par
  B5), code de sortie non nul si une étape critique échoue
- Le pipeline est une suite d'appels de fonctions dans un seul fichier ;
  l'automatisation = ce fichier dans un ordonnanceur externe (CronJob du
  catalogue Onyxia ou schedule GitLab CI), sans une ligne à réécrire
- Le cron se pose dans la dernière heure du hackathon, seulement si la démo
  est validée

### B10 — Extensions · à ouvrir seulement si B1-B9 tiennent

Par ordre de rentabilité :

1. **Questions au Gouvernement** (écrites, orales) : même pipeline, autre
   source, mapping de champs à écrire — MÉTIER identifie les champs utiles,
   un étudiant code le mapping. Texte riche, excellent rapport signal/effort.
2. **Agenda des réunions** : veille d'anticipation ("votre thème passe en
   commission demain"), petit texte, digest séparé.
3. **Agent de consultation** : un plugin maubot interactif qui répond aux
   questions de suivi dans le salon ("où en est ce texte ? qui est
   l'auteur ?") via le serveur MCP Parlement de Tricoteuses. Complément
   pull du produit push, jamais son remplacement.
4. **Sénat** : si l'option Tricoteuses est retenue en B1, changement de
   dépôt Git, pas de nouveau pipeline.
5. **Comptes rendus** : le plus riche mais hors schéma (flux Syceron),
   parsing ad hoc garanti. Dernier de la liste.

## Ordre de marche

Calé sur le programme officiel (~8 h de code vendredi, ~4 h samedi,
gel à 14h, restitution de 3 minutes à 16h) — détail dans
docs/organisation.md :

- **Avant vendredi 14h** : B0, compte bot Tchap demandé.
- **Vendredi 14h-19h** : spike Tricoteuses, puis B1, B2 et B7 en
  parallèle ; B3 et B5 dans la foulée. Jalon du dîner : run partiel
  fetch → clean → lexical → Grist depuis main.
- **Vendredi soir** : B4 et B6. Jalon 22h30 : le premier digest tombe
  dans le salon Tchap.
- **Samedi 9h45-13h30** : B4 finalisé si besoin, B8 compact, polissage ;
  gel interne 13h30, puis script de restitution et deux répétitions.
- B10 pour les mains libres uniquement, sans toucher à main.

À 3 personnes : DEV = B0 + B4 + B9, DATA = B1 + B2 + B3 + B8,
MÉTIER = B7 + B6. À 12 : un bloc par personne, étudiants en binôme sur
B1, B2, B5 et B6.

## Décisions actées — on en reparle volontiers, après la restitution

Chaque réouverture en cours de route coûte une synchro à douze.

- **Source** : dépôts Git Tricoteuses (option A actée, fichiers JSON
  éclatés validés) ; le dump officiel reste codé en fallback, bascule par
  variable d'environnement. Pas de CSV fil-de-l'eau : notre promesse est
  J+1, pas le temps réel.
- **MCP** : pas le produit. La veille est un balayage exhaustif push avec
  garantie de rappel ; un MCP est du pull best-effort pour agent
  conversationnel. Réutilisé en B10.3 comme complément de consultation.
- **Stockage** : Grist est le front utilisateur (config, résultats,
  historique, vues) ; la source Git/zip est la donnée, re-téléchargeable ;
  `data/` local n'est qu'un cache. Besoin futur de stockage intermédiaire →
  Parquet sur le S3 d'Onyxia (décision différée, défaut nommé).
- **Matching** : lexical en Python pur pour les mots-clés (garantie de
  rappel), métadonnées pour parlementaire/dossier, Albert search pour les
  thèmes. Le LLM juge complète l'extrait cité, ne le remplace jamais.
- **Notification** : compte Tchap dédié (adossé à une BALF, procédure
  documentée par la communauté Tchap et le retour d'expérience SSPhub) piloté
  par `simplematrixbotlib`. Pour le digest, pas de bot qui écoute : une
  fonction send-only appelée en fin de run.py, qui ne demande rien à
  héberger ; maubot viendra avec le bot interactif (B10.3), qui réutilisera
  le même compte. Prérequis tiers à lancer immédiatement :
  création de la BALF et du compte. Fallback si le compte n'arrive pas à
  temps : digest par mail, l'envoi étant isolé derrière une fonction unique.
- **No-code renforcé** : les colonnes calculées Grist (formules Python dans
  Grist) sont le territoire de MÉTIER — liens construits depuis l'uid,
  compteurs — sans toucher au dépôt. Pas de widget custom : les vues
  standard suffisent.
- **Orchestration** : `run.py` manuel pendant le hackathon, cron externe
  ensuite. Pas de n8n, pas de scheduler maison, pas de framework.
- **Hors scope assumé** face aux offres privées : temps réel < 30 min,
  presse et audiovisuel, transcription vidéo, cartographie des décideurs.
  Notre périmètre : ciblage (mot-clé, thème, parlementaire, dossier),
  digest sourcé, suivi du sort — entièrement sur briques de l'État.
