# Issues à créer — copier-coller si l'import CSV n'est pas utilisé

## B1 — Acquisition (Tricoteuses, fallback dump AN)

**Profil** : DATA ou débutant · **Dépend de** : B0 · **Branche** : `feature/b1-acquisition`

Option A actée : dépôt Git Tricoteuses `assemblee-brut/Amendements_XVII` (schéma AN brut, un JSON par amendement).

- [ ] `git clone --depth 1` du dépôt, chemin configurable par variable d'env
- [ ] Incrémental : `git pull` puis `git diff --name-only ORIG_HEAD HEAD` = liste des fichiers nouveaux/modifiés
- [ ] Fallback option B (dump officiel, déjà codé dans `fetch.py`) activable par `VEILLE_SOURCE=dump`
- [ ] Mesurer taille du clone et fraîcheur réelle, consigner dans DECISIONS.md

**Contrat de sortie** : liste de chemins de fichiers JSON à passer à B2.

---

## B2 — Nettoyage et extraction : validation sur échantillon large

**Profil** : DATA · **Dépend de** : B1 · **Branche** : `feature/b2-clean`

`strip_html` et `extract_amendement` sont écrits et testés (12 tests). Le travail du bloc est la validation à l'échelle.

- [ ] Passer `extract_amendement` sur un échantillon large (>1000 fichiers) et lister les KeyError / champs vides
- [ ] Vérifier le chemin du `sort` sur des amendements votés (les exemples frais sont « En traitement »)
- [ ] Repérer les dispositifs structurés (amendements de crédits) ; ne coder le fallback fragmenthtml que si le cas apparaît
- [ ] Ajouter 1-2 JSON réels problématiques dans `tests/data/` avec leur test

**Contrat** : dict « document propre » (voir docs/architecture.md).

---

## B3 — Matching lexical et métadonnées

**Profil** : DATA · **Dépend de** : B2 · **Branche** : `feature/b3-lexical`

- [ ] `match_lexical.py` : recherche insensible à la casse dans exposé + dispositif ; extrait = phrase contenant le terme ; un terme d'`exclusions` présent annule le match
- [ ] `match_meta.py` : égalité souple (casse, espaces) sur auteur / texte_ref ; extrait = champ matché
- [ ] Test couvrant : accents, casse, entité résiduelle, exclusion qui annule

Python pur, pas de rapidfuzz. La valeur du bloc est sa prévisibilité (garantie de rappel).

---

## B4 — Matching sémantique (Albert)

**Profil** : DEV · **Dépend de** : B2 · **Branche** : `feature/b4-semantique`

- [ ] Une collection par run (nommée par date/label), purge des anciennes reportée après le hackathon
- [ ] `POST /v1/documents` avec `disable_chunking=true`, texte = exposé + dispositif tronqué à 8 000 caractères, metadata = uid, texte_ref, date_depot
- [ ] `POST /v1/search` method=hybrid par veille `theme` active, top-k
- [ ] Score renormalisé 0-100 ; extrait = chunk entier dans Grist, ~300 caractères dans le digest
- [ ] Vérifier quotas réels via `GET /v1/me/info` avant le premier gros run

Pas de reranker tant que B8 n'en montre pas le besoin.

---

## B5 — Écriture Grist

**Profil** : débutant encadré · **Dépend de** : contrats seulement · **Branche** : `feature/b5-grist`

- [ ] Lecture de `veilles`, écriture de `resultats` par lots (`POST /api/docs/{doc}/tables/{table}/records`)
- [ ] Idempotence : jamais de réinsertion d'une paire (uid, veille) existante
- [ ] Suivi du sort : si le `sort` du dump diffère de la base, mettre à jour et renseigner `evolution`
- [ ] Un test du diff d'idempotence, un test du changement de sort

requests uniquement, pas de client tiers.

---

## B6 — Digest Tchap

**Profil** : MÉTIER + étudiant · **Dépend de** : B5 · **Branche** : `feature/b6-digest`

⚠️ Calendrier réel : le digest v1 doit tomber dans le salon **J1 au soir**, pas J2 matin.

- [ ] Agrégation des résultats du jour par texte législatif ; top 5 par veille trié par score, format « titre + deux lignes + lien »
- [ ] Section « évolutions » (sorts changés) ; lien par veille vers la vue Grist filtrée
- [ ] Envoi send-only via `send_markdown_message` (extra `tchap`) ; fallback mail derrière la même fonction
- [ ] MÉTIER : gabarit markdown, arbitrage du contenu, test de lisibilité sur mobile
- [ ] Cas déluge (PLF) : annoncer le volume, montrer le top, jamais de liste brute

---

## B7 — Configuration et vues Grist

**Profil** : MÉTIER, aucun code · **Aucune dépendance — démarre immédiatement**

- [ ] Rédiger 5+ veilles réelles : mots-clés avec variantes et exclusions, thèmes en français
- [ ] Vues Grist : résultats par veille, par texte, par auteur ; mini tableau de bord
- [ ] Qualifier les résultats via la colonne `pertinent` (vérité terrain de B8)
- [ ] Colonnes calculées (liens depuis l'uid, compteurs) : territoire MÉTIER, sans toucher au dépôt

---

## B8 — Évaluation et calibration (version compacte)

**Profil** : DATA · **Dépend de** : B1-B4 et B7 · **Branche** : `feature/b8-eval`

Calendrier réel oblige : pas de backfill complet de la législature. Cibler.

- [ ] Backfill sur UN dossier législatif riche ou un mois de dépôts
- [ ] Précision/rappel par méthode sur les veilles qualifiées ; calibrer top-k
- [ ] Produire LE chiffre du pitch : « X détectés, dont Y sans mention littérale du terme »
- [ ] Notebook `#%%` dans `notebooks/`, conclusions en markdown

---

## B9 — Orchestration

**Profil** : DEV · **Dépend de** : tout · **Branche** : `feature/b9-run`

`run.py` est déjà câblé sur les stubs.

- [ ] Option `--date`, code de sortie non nul si étape critique échoue
- [ ] Vérifier la relance sans doublons (garantie B5) sur un run réel
- [ ] Cron externe (Onyxia / GitLab CI) : uniquement après validation de la démo, dernière heure

---

## B10 — Extensions (mains libres uniquement)

À ouvrir seulement si B1-B9 tiennent. Ne touche pas à main avant le gel.

1. Questions au Gouvernement (même pipeline, mapping à écrire)
2. Agenda des réunions (veille d'anticipation)
3. Agent de consultation maubot + MCP Parlement
4. Sénat (changement de dépôt Tricoteuses)
5. Comptes rendus (flux Syceron, parsing ad hoc)

---

## [debutant] Gabarit markdown du digest

Rédiger le gabarit du digest Tchap dans `src/veille/templates/` : en-tête daté, section par veille (titre + 2 lignes + lien), section évolutions, pied avec lien Grist. Tester le rendu markdown dans un salon Tchap de test. Aucune dépendance au pipeline.

---

## [debutant] Inventaire des champs du JSON réel

Prendre 20 amendements variés dans le dépôt Tricoteuses (dont : de suppression, de crédits, cosignés, rectifiés) et documenter dans `docs/champs_json.md` les chemins présents/absents. C'est l'assurance-vie de B2.

---

## [debutant] Veilles d'exemple

Avec le référent MÉTIER : saisir dans Grist 5 veilles réalistes couvrant les 4 types (mot_cle avec exclusions, theme, parlementaire, dossier). Vérifier que chaque champ du contrat de la table `veilles` est exercé.

---

## [debutant] Test de bout en bout sur 2 JSON commités

Écrire un test pytest qui enchaîne extract_amendement → match_lexical sur les JSON de `tests/data/` avec une veille en dur, et vérifie la ligne de résultat produite (uid, extrait, methode).

---

