# Issues à créer — copier-coller si l'import CSV n'est pas utilisé

## B1 — Recherche et écriture Grist

**Profil** : DEV ou DATA · **Dépend de** : B0 · **Branche** : `feature/b1-recherche-grist`

Remplace les anciens blocs d'acquisition, de nettoyage et de matching
(lexical, métadonnées, sémantique) : l'API Tricoteuses fait la recherche
server-side, il n'y a plus de pipeline local à écrire pour ça.

- [ ] Pour chaque veille active (`veilles.actif = true`), un appel
  `fetch_api.fetch_mots_cles(source, jour, liste)` (ou `fetch_jour` si
  `liste` vide) sur la ressource `source`
- [ ] Filtrage local : un terme d'`exclusion` présent dans le texte annule
  le résultat
- [ ] Extrait de citation : phrase du texte contenant le terme recherché
- [ ] `grist.py` : lecture de `veilles`, écriture de `resultats` par lots
  (`POST /api/docs/{doc}/tables/{table}/records`)
- [ ] Idempotence : jamais de réinsertion d'une paire (uid, veille)
  existante
- [ ] Suivi du sort : si le `sort` renvoyé par l'API diffère de celui déjà
  en base, mettre à jour et renseigner `evolution`
- [ ] Un test du filtrage par exclusion, un test du diff d'idempotence, un
  test du changement de sort

**Contrats** : table `veilles`, table `resultats` (voir
`docs/architecture.md`). Outils : `veille.fetch_api` (déjà écrit),
`requests` sur l'API Grist — voir `docs/api-tricoteuses.md` et
`docs/api-grist.md`.

---

## B2 — Digest Tchap

**Profil** : MÉTIER + étudiant · **Dépend de** : B1 et B4 · **Branche** : `feature/b2-digest`

⚠️ Calendrier réel : le digest v1 doit tomber dans le salon **J1 au soir**.

- [ ] Le paragraphe de synthèse d'Albert (B4) ouvre le digest
- [ ] Agrégation des résultats du jour par texte législatif ; top 5 par
  veille trié par `date_depot`, format « titre + deux lignes + lien »
- [ ] Section « évolutions » (sorts changés) ; lien par veille vers la vue
  Grist filtrée
- [ ] Envoi send-only via `send_markdown_message` (extra `tchap`) ;
  fallback mail derrière la même fonction — voir
  `docs/api-tchap-maubot.md`
- [ ] Le digest part même si la synthèse Albert manque (panne, quota)
- [ ] MÉTIER : gabarit markdown, arbitrage du contenu, test de lisibilité
  sur mobile
- [ ] Cas déluge (PLF) : annoncer le volume, montrer le top, jamais de
  liste brute

---

## B3 — Configuration et vues Grist

**Profil** : MÉTIER, aucun code · **Aucune dépendance — démarre immédiatement**

- [ ] Rédiger 5+ veilles réelles : `mot_cle` avec variantes et exclusions,
  `sujet` en français, `parlementaire`, `dossier`
- [ ] Vues Grist : résultats par veille, par texte, par auteur ; mini
  tableau de bord (volumes par jour, répartition par source) — voir
  `docs/dashboards.md`
- [ ] Qualifier les résultats via la colonne `pertinent`
- [ ] Colonnes calculées (liens depuis l'uid, compteurs) : territoire
  MÉTIER, sans toucher au dépôt

---

## B4 — Synthèse par Albert API

**Profil** : DEV ou DATA · **Dépend de** : B1 et B3 · **Branche** : `feature/b4-synthese-albert`

Remplace l'ancien bloc d'évaluation et calibration : Albert n'est plus un
moteur de recherche, c'est l'outil de synthèse du digest.

- [ ] `POST /v1/chat/completions` (Mistral-Small-3.2-24B) à chaque run,
  prompt limité aux `extrait` des lignes `resultats` du jour, regroupées
  par veille — voir `docs/api-albert.md`
- [ ] Paragraphe de 3-5 phrases en français, jamais un fait hors des
  extraits fournis
- [ ] Vérifier les quotas réels via `GET /v1/me/info` avant le premier
  run en volume
- [ ] Bascule propre si Albert est indisponible : digest sans synthèse

---

## B5 — Orchestration

**Profil** : DEV · **Dépend de** : tout · **Branche** : `feature/b5-run`

`run.py` est déjà câblé sur les stubs.

- [ ] Enchaîner veilles (Grist) → recherche + écriture (B1) → synthèse
  Albert (B4) → digest (B2)
- [ ] Option `--date`, code de sortie non nul si étape critique échoue
- [ ] Vérifier la relance sans doublons (garantie B1) sur un run réel
- [ ] Cron externe (Onyxia / GitHub Actions) : uniquement après validation
  de la démo, dernière heure

---

## B6 — Extensions (mains libres uniquement)

À ouvrir seulement si B1-B5 tiennent. Ne touche pas à main avant le gel.

1. Questions au Gouvernement (même bloc B1, `source = questions`)
2. Agenda des réunions (`source = reunions`, veille d'anticipation)
3. Agent de consultation maubot + MCP Parlement
4. Sénat (ressources `senat-*` de l'écosystème Tricoteuses)
5. Comptes rendus (flux Syceron, parsing ad hoc)

---

## [debutant] Gabarit markdown du digest

Rédiger le gabarit du digest Tchap dans `src/veille/templates/` : en-tête
daté, paragraphe de synthèse, section par veille (titre + 2 lignes +
lien), section évolutions, pied avec lien Grist. Tester le rendu markdown
dans un salon Tchap de test. Aucune dépendance au pipeline.

---

## [debutant] Inventaire des champs de l'API Tricoteuses

Interroger 20 amendements variés via `parlement.tricoteuses.fr/v2` (dont :
de suppression, de crédits, cosignés, rectifiés) et documenter dans
`docs/champs_api.md` les champs présents/absents. C'est l'assurance-vie
de B1.

---

## [debutant] Veilles d'exemple

Avec le référent MÉTIER : saisir dans Grist 5 veilles réalistes couvrant
les 4 types (`mot_cle` avec exclusions, `sujet`, `parlementaire`,
`dossier`). Vérifier que chaque colonne du contrat de la table `veilles`
est exercée.

---

## [debutant] Test de bout en bout sur un jour réel

Écrire un test pytest qui enchaîne `fetch_api.fetch_mots_cles` → filtrage
par exclusion sur une veille en dur, et vérifie la ligne de résultat
produite (uid, extrait).
