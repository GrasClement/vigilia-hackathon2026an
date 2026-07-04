# Veille parlementaire — Architecture et découpage en blocs

Version révisée après la spec B2 : le LLM produit le **message Tchap
complet** de chaque veille (B4), la publication (B5) devient un envoi
pur. La priorisation des amendements passe par le reranker Albert avec
repli déterministe. Ce document est la référence du dépôt : tout nouveau
contributeur le lit avant d'écrire une ligne de code. Les changements par
rapport à la version précédente sont consignés dans `DECISIONS.md`.

## Le projet en trois phrases

Chaque administration, chercheur ou citoyen décrit ses sujets d'intérêt —
et *pourquoi* ils l'intéressent — dans un tableau Grist (mot-clé, sujet,
parlementaire ou dossier, plus un objectif en une phrase), et reçoit
chaque matin sur Tchap un message sourcé des travaux de l'Assemblée qui
le concernent : synthèse rédigée par Albert selon l'objectif déclaré,
chiffres clés calculés en Python, priorités justifiées, liens vers les
amendements. Le système suit également le devenir des documents détectés
(amendement adopté, rejeté). Tout repose sur l'open data de l'Assemblée
via l'API Tricoteuses et les briques souveraines de l'État : Grist,
Albert API, Tchap, hébergement Onyxia.

## Flux dans l'architecture

```
Grist (table veilles)                       API Tricoteuses (v2)
  id / type / liste / actif / source /  ──────►  recherche + filtre de date
  exclusion / objectif                            par ressource
        │                                                │
        │  B1 lit les veilles actives                    │
        ▼                                                ▼
                    B1 — un appel par veille active
                    filtrage local des `exclusion`
                              │
                              ▼
              Grist (table resultats) — nouvelles lignes
              (schéma riche : textes complets inclus)
                              │
                              ▼
              B1.5 — suivi du sort (uid déjà en base)
              met à jour `sortAmendement` et `evolution`
                              │
                              ▼
        B4 — génération du message complet (Albert)
     stats Python → ordre /v1/rerank → niveaux déterministes
     → rédaction /v1/chat/completions (gabarit défini par B2)
     → repli : message de secours si Albert indisponible
                              │
                              ▼
              B5 — envoi sur Tchap (send-only)
           un message markdown par veille active
                              │
                              ▼
                Tchap (salon de diffusion)
```

B2 (design du message) et B3 (configuration Grist) ne sont pas des
étapes d'exécution : ce sont des contrats d'entrée. B2 fournit le gabarit
que B4 implémente, B3 fournit les veilles (dont `objectif`) et les vues.

Documentation par API :

- [`docs/api-tricoteuses.md`](api-tricoteuses.md) — acquisition et
  recherche server-side (B1)
- [`docs/api-grist.md`](api-grist.md) — lecture des veilles, écriture et
  mise à jour des résultats (B1, B1.5, B3)
- [`docs/synthese-design.md`](synthese-design.md) — gabarit du message
  (B2, spec figée)
- [`docs/api-albert.md`](api-albert.md) — chat completions et rerank (B4)
- [`docs/synthese-b4.md`](synthese-b4.md) — la brique B4 elle-même
- [`docs/api-tchap-maubot.md`](api-tchap-maubot.md) — envoi (B5)
- [`docs/dashboards.md`](dashboards.md) — vues Grist (B3)

## Profils de contributeurs

- `DEV` : Python confirmé. Blocs touchant aux API externes et à
  l'assemblage.
- `DATA` : à l'aise en notebook. Écriture Grist, suivi du sort,
  génération du message.
- `MÉTIER` : connaissance de l'Assemblée, pas de code. Configuration
  Grist, qualification des résultats, spec du message, test de
  lisibilité. Ce profil porte la démonstration "no code".

## Contrats d'interface

Toute modification d'un contrat se décide en synchro d'équipe et se
consigne dans `DECISIONS.md`.

### Table Grist `veilles` — éditée par MÉTIER (B3), lue par B1 et B4

```
id | type | liste | actif | source | exclusion | objectif
```

- `type` : `mot_cle`, `sujet`, `parlementaire` ou `dossier`.
- `liste` : valeurs recherchées, séparées par des virgules.
- `exclusion` : termes annulant un résultat (seul filtrage client
  restant, l'API Tricoteuses n'a pas de NOT).
- `objectif` : texte libre décrivant l'intention de la veille. Fourni
  tel quel à B4 : il sert de query au reranker et de grille de lecture à
  la synthèse. Vide = ordre par date et résumé neutre.

### Table Grist `resultats` — écrite par B1, mise à jour par B1.5, lue par B4 et les vues

Schéma riche, textes complets inclus (décision actée : le message de B4
a besoin du dispositif et de l'exposé sommaire, pas seulement d'un
extrait) :

```
uid | typeAuteur | dispositif | exposeSommaire | sortAmendement |
etatLibelle | nombreCoSignataires | dateDepot | auteur_uid | auteur_nom |
auteur_prenom | auteur_civ | auteur_chambre | groupe_politique |
groupe_politique_abrege | couleur_politique | document_uid |
dossier_ref_uid | titre_dossier | titre_dossier_court | filtres_trouves |
jour_veille | veille_id | veille_nom | veille_termes | veille_noms |
veille_dossiers | veille_source | evolution | pertinent
```

- Une ligne par paire document × veille ; un document touchant deux
  veilles produit deux lignes. C'est voulu.
- `filtres_trouves` : quels termes ont déclenché la détection —
  l'explicabilité native du système.
- `evolution` : renseignée par B1.5 quand `sortAmendement` change après
  détection ("adopté le JJ/MM").
- `pertinent` : oui/non/vide, rempli à la main par MÉTIER ; vérité
  terrain pour ajuster les veilles.
- Pas de colonne URL : l'URL se construit depuis `uid` (fonction Python
  côté pipeline, colonne calculée Grist côté vues).

### Sortie de B4 — entrée de B5

Une chaîne markdown par veille active, **jamais vide** : le message
complet (gabarit B2), ou le message fixe "aucun amendement", ou le
message de secours avec bandeau d'échec si Albert est indisponible. B5
n'a aucune logique conditionnelle : il envoie ce qu'il reçoit.

## Blocs de travail

### B0 — Socle du dépôt · DEV

Inchangé : pyproject UV, ruff, layout `src/veille/`, `.env.example`
(`ALBERT_API_KEY`, `GRIST_API_KEY`, `GRIST_DOC_ID`, `TCHAP_BOT_MATRIX_ID`,
`TCHAP_BOT_PWD`), doc Grist conforme aux contrats, salon Tchap, spike
Tricoteuses, `DECISIONS.md`.

### B1 — Recherche et écriture Grist · DEV ou DATA · dépend de B0

Un appel Tricoteuses par veille active ; filtrage `exclusion` local ;
écriture des **nouvelles** lignes de `resultats` avec les textes
complets ; idempotence sur (uid, veille) — c'est ce qui rend le pipeline
relançable. Un test du filtrage, un test du diff d'idempotence.

### B1.5 — Suivi du sort · DATA · dépend de B1

Comparer le `sortAmendement` renvoyé par l'API pour les `uid` en base ;
si changé, PATCH de la ligne et renseignement d'`evolution`. Un test
dédié.

### B2 — Design du message · MÉTIER · aucune dépendance, spec figée

Produit `docs/synthese-design.md`, contrat d'entrée de B4. **Acté** : le
LLM rédige le message complet (📌 Veille, Synthèse, Chiffres clés,
Priorités, Amendements à ouvrir, Limites), les chiffres viennent
exclusivement du JSON de stats Python, les niveaux de priorité sont
fournis et non jugés, le cas déluge est géré en amont (voir B4).

### B3 — Configuration et vues Grist · MÉTIER · aucune dépendance

Inchangé : veilles réelles de démonstration (chacune avec `objectif` —
désormais doublement utile : query du reranker et grille de la
synthèse), chart widgets et linked widgets, qualification `pertinent`.

### B4 — Génération du message · DEV ou DATA · dépend de B1, B1.5, B2, B3

Module `src/veille/synthese.py`, point d'entrée
`generer_message(contexte, amendements) -> str`. Pipeline interne :
stats Python → ordre par `/v1/rerank` (query = objectif, replis :
`veille_termes` puis tri par date) → niveaux Forte/Moyenne/Faible
déterministes → K = 25 amendements en texte intégral, le reste en une
ligne → rédaction par Mistral-Small (temp 0.2, 2 500 tokens) → message de
secours à bandeau si échec. Détail : `docs/synthese-b4.md`. Deux appels
API par veille, dans les quotas Expérimentation.

### B5 — Envoi sur Tchap · MÉTIER + étudiant · dépend de B4

`digest.py` réduit à l'envoi : pour chaque veille active, poster le
message de B4 via `send_markdown_message` (markdown rendu nativement).
Aucune mise en forme, aucune logique de repli — B4 garantit un message
non vide dans tous les cas. MÉTIER : tester la lisibilité sur mobile,
arbitrer l'ordre d'envoi des veilles.

### B6 — Orchestration · DEV · dépend de tout, volontairement trivial

`run.py` : `veilles (Grist) → B1 → B1.5 → boucle par veille active
[B4 → B5]`, séquentiel (pas de parallélisme, les quotas et le volume ne
le justifient pas), options `--date` et `--veille` (une seule veille,
pour les tests de prompt sans consommer le RPD), relançable sans
doublons, code de sortie non nul si une étape critique échoue.

### B7 — Extensions · si B0-B6 tiennent

Inchangé : autres corpus Tricoteuses ; RAG sur les résultats accumulés ;
mode conversationnel ; maubot interactif ; widget Grist custom. S'y
ajoute : rerank comme tie-breaker configurable de la bande "Moyenne"
(hors chemin principal).

## Ordre de marche

Inchangé (détail dans docs/organisation.md) : B0 avant vendredi 14h ;
B1, B1.5, B3 et B2 en parallèle vendredi après-midi ; B4 puis B5
vendredi soir (jalon 22h30 : premier message complet dans le salon) ;
polissage et B6 samedi matin, gel 13h30.

## Décisions actées — on en reparle volontiers, après la restitution

- **Source et recherche** : API REST Tricoteuses, filtre de date et
  recherche plein texte server-side. Un appel par veille. Promesse J+1,
  pas de temps réel.
- **Périmètre B4/B5** *(révisé)* : B4 produit le message Tchap complet
  par veille selon la spec B2 ; B5 est send-only. Remplace l'ancien
  partage "B4 = paragraphe, B5 = assemblage du digest".
- **Données du prompt** *(révisé)* : B4 lit les textes complets
  (dispositif, exposé sommaire) depuis Grist `resultats`. Les garanties
  anti-hallucination sont désormais : chiffres du JSON de stats
  uniquement, faits des textes fournis uniquement, URLs construites en
  Python. Remplace "extraits seuls, jamais le document complet".
- **Priorisation** *(révisé)* : ordre sémantique par `/v1/rerank`
  (query = `objectif`, repli `veille_termes`, repli tri `dateDepot`),
  niveaux Forte/Moyenne/Faible calculés en Python sur des colonnes
  justifiables (sort notable, député suivi, filtres). Le LLM rédige, ne
  juge pas. Remplace "tri par date, pas de score".
- **Cas déluge** *(révisé)* : plafond K = 25 en texte intégral côté
  Python, stats sur la totalité, le prompt annonce le volume. Remplace
  les seuils 50/200 en instruction au LLM.
- **Échec Albert** *(révisé)* : le message part toujours — gabarit de
  secours déterministe avec bandeau d'échec explicite. Remplace "chaîne
  vide gérée par B5".
- **Modèle** : `mistralai/Mistral-Small-3.2-24B-Instruct-2506` par
  défaut, configurable ; gpt-oss-120b écarté (10 RPM, tokens de
  raisonnement). Arbitrage sur pièces possible.
- **Stockage** : Grist front utilisateur ; Tricoteuses ré-interrogeable ;
  pas de cache disque. Besoin futur → Parquet sur S3 Onyxia.
- **Notification** : compte Tchap dédié, fonction send-only en fin de
  run ; maubot seulement pour le bot interactif (B7). Fallback mail.
- **No-code renforcé** : colonnes calculées Grist = territoire de MÉTIER
  (liens depuis l'uid, compteurs). Pas de widget custom dans le cœur.
- **Orchestration** : `run.py` manuel pendant le hackathon, cron externe
  ensuite. Pas de n8n, pas de framework.
- **Hors scope assumé** : temps réel < 30 min, presse, transcription,
  cartographie des décideurs.