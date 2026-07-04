# Organisation du hackathon — équipe, rythme et contributions

Version finale. Complément du document d'architecture
(`blocs_projet_veille_parlementaire.md`). Hypothèse de travail : deux jours
sur place, 3 à 12 personnes à géométrie variable, majoritairement étudiants,
pas de profil devops — d'où un principe unique qui gouverne tout ce qui
suit : rien ne doit exiger d'infrastructure à maintenir, tout doit être
relançable à la main par n'importe qui.

## Rôles

Deux rôles nommés, pas davantage.

- **Intégrateur** (porteur du projet) : seul à merger sur main, tranche les
  litiges de contrat, tient `DECISIONS.md`, réalimente la file d'issues.
  C'est un rôle de gardien des interfaces, pas de chef de projet : les blocs
  se coordonnent par leurs contrats, pas par des réunions.
- **Référent Grist** (profil MÉTIER) : propriétaire des tables et des vues.
  La structure des tables passe par lui : un seul propriétaire, zéro
  collision — c'est le pendant humain du contrat d'interface. Les vues et
  colonnes calculées, en revanche, sont ouvertes à tous.

Tous les autres : owner d'un bloc, donc de son issue et de sa branche.

## Avant le jour 1 — la liste bloquante

Environ une demi-journée du porteur. Rien ici n'est rattrapable sur place.

1. **B0 poussé** : le dépôt s'installe en trois commandes sur une machine
   vierge (tester réellement sur une machine vierge, un service VSCode
   Onyxia neuf fait l'affaire).
2. **Les trois accès prouvés** : un `curl` réussi vers Albert
   (`GET /v1/me/info`, qui donne au passage les quotas réels du compte),
   vers l'API Grist, et vers le webhook maubot. Captures dans le README :
   pour des étudiants, la preuve que "ça marche déjà" vaut toutes les docs.
3. **Compte bot Tchap obtenu** : Tchap est une fédération fermée, la
   procédure peut prendre du délai — c'est le seul prérequis du projet qui
   dépend d'un tiers. Lancer la demande immédiatement ; fallback mail codé
   si elle n'aboutit pas à temps.
4. **Spike API Tricoteuses `amendements`** (1 h chrono, bloc B0) : confirmer
   la fraîcheur, la pagination et la forme des réponses sur un jour réel,
   consigner dans `docs/api-tricoteuses.md` et `DECISIONS.md`.
5. **Salon Tchap d'équipe** créé, distinct du salon de diffusion du digest: https://tchap.gouv.fr/#/room/!FrtxQRJxngbuBLxKzS:agent.tchap.gouv.fr?via=agent.tchap.gouv.fr
6. **File d'issues amorcée** : les blocs B0 à B7 (dont B1.5, voir
   `docs/architecture.md`), plus trois ou quatre issues étiquetées
   `debutant` (gabarit du digest, veilles d'exemple, inventaire des champs de la ressource `questions` pour l'extension B7.1).
7. **MÉTIER préparé** : a lu la doc open data AN et rédigé cinq veilles
   réelles brouillon.

## Rythme quotidien

Trois synchros debout de dix minutes sur l'ensemble du week-end,
chronométrées. Tout le reste passe par Tchap et les issues.

- **Vendredi 14h — attribution.** Qui prend quoi, sur le tableau GitLab.
  Un nouvel arrivant est mis en binôme avec un owner de bloc, ou
  l'intégrateur lui propose une issue prête, pour lui épargner
  l'exploration du backlog.
- **Vendredi 19h (dîner) — intégration.** Le pipeline (ou ce qui en
  existe) est lancé devant tout le monde depuis main. Ce qui n'est pas
  mergé se merge là. Ce rituel garantit que main reste démontrable en
  permanence.
- **Samedi 9h45 — reprise.** État des lieux, réattribution pour les
  quatre heures restantes.

La synchro de mi-journée est remplacée par la règle des trente minutes
sur Tchap : bloqué plus de trente minutes, on le dit. Personne ne
s'enterre — c'est la règle la plus importante du week-end pour une
équipe étudiante.

Toute modification d'un contrat d'interface se décide en synchro et se
consigne dans `DECISIONS.md` (une ligne par décision, datée). Jamais dans un
commit isolé.

## Workflow de contribution

- Une issue par bloc ; la checklist de l'issue est la liste de tâches du
  document d'architecture.
- Branche `feature/<bloc>-<sujet>` ; MR ouverte en brouillon dès le premier
  commit, pour que le travail soit visible sans être jugé fini.
- Review volontairement légère, deux questions et deux seulement : est-ce
  que ça tourne sur un cas réel ? est-ce que le contrat est respecté ? Le
  style est l'affaire de ruff, pas des humains.
- Merge par l'intégrateur uniquement.
- Géométrie variable : quand quelqu'un part, son état est mergé avant son
  départ, même imparfait, quitte à le marquer TODO. Du code non mergé sur
  un laptop absent n'existe pas.
- Les binômes committent sous leurs deux noms (Co-authored-by) : la
  contribution des étudiants doit être visible dans l'historique.

## Absorber une équipe de 3 à 12

Le goulot d'un hackathon n'est jamais le nombre de mains, c'est le nombre de
tâches prêtes à être prises. La file `debutant` doit contenir en permanence
deux ou trois issues non attribuées ; l'intégrateur la réalimente à chaque
synchro. Tâches parallélisables sans dépendance, idéales pour un arrivant :
veilles supplémentaires et vues Grist, tests sur données réelles, gabarits
de digest, backfill de B8, exploration du dump questions (B10.1), relecture
du pitch. Un arrivant présent une demi-journée ne touche pas aux blocs cœur
(B4, B9) : on lui propose mieux — une tâche qu'il peut finir et signer
dans sa demi-journée.

## Déroulé réel (programme officiel)

Le programme donne environ huit heures de code vendredi (14h-23h, dîner
déduit) et quatre samedi (9h45-14h, gel imposé par l'organisation), avec
une restitution de trois minutes par défi à 16h, en présence de la
Présidente. Conséquence structurante : le jalon principal se joue
vendredi soir, pas samedi.

**Vendredi 3 juillet.** 13h30 : pitch d'une minute du défi. 14h :
attribution des blocs et installation — le dépôt s'installe en trois
commandes, c'est le moment de le prouver — puis spike API Tricoteuses
(forme des réponses, fraîcheur, consignées dans DECISIONS.md). B1, B3 et
B2 (design de la synthèse) en parallèle dès 14h30 ; B1.5 démarre dès que
B1 a écrit ses premières lignes. **Jalon 19h (dîner)** : run partiel
recherche Tricoteuses → Grist (B1) depuis main. Après le dîner : B4
(génération) puis B5 (publication). **Jalon 22h30 : le premier digest,
synthèse Albert comprise, tombe dans le salon Tchap.** Samedi n'a que
quatre heures de code, le produit doit exister vendredi soir. Avant de
partir : tout est mergé.

**Samedi 4 juillet.** 9h45 : polissage B4/B5, B6 (orchestration).
**13h30 : gel interne**, trente minutes avant le gel officiel de 14h :
captures d'écran, tag git. 14h-16h : script de restitution — la
séquence Grist → run.py → Tchap tient exactement dans les trois
minutes — et deux répétitions chronométrées. 16h : restitution.


## Démo et plans B

- La démo se joue depuis le cache `data/` : les données du jour sont
  téléchargées la veille au soir, aucune dépendance au réseau du lieu pour
  l'acquisition.
- Séquence de trois minutes, qui est exactement le pitch : MÉTIER ajoute une
  veille en direct dans Grist → `run.py` → le digest tombe dans Tchap avec
  l'extrait justificatif → vue Grist des résultats et du suivi des sorts.
  No-code, explicabilité, souveraineté : tout y est, sans slide.
- Le chiffre de B8 ("X détectés, dont Y sans mention littérale du terme")
  est sur un slide, jamais recalculé en direct.
- Plans B par étage : Albert indisponible → démo lexical + métadonnées
  seules, le pipeline tourne quand même ; Tchap indisponible → montrer la
  table Grist ; tout indisponible → captures d'écran faites au gel
  interne de 13h30.

## Risques et parades

| Risque | Parade |
|---|---|
| Compte bot Tchap pas obtenu à temps | Demande lancée dès maintenant ; fallback mail derrière la même fonction d'envoi |
| Quotas Albert atteints | Volumes réels testés à J0 via `/v1/me/info` ; top-k dès le premier run |
| Réseau du lieu capricieux | Cache disque ; dump téléchargé la veille au soir |
| Tricoteuses indisponible le jour J | Option B (dump officiel) codée en fallback, bascule par variable d'env |
| Contrat modifié en douce | Merge par l'intégrateur seul ; contrats dans le document d'architecture |
| Étudiant perdu ou inoccupé | File `debutant` réalimentée ; binômes ; règle des trente minutes |
| Dérive de périmètre | `DECISIONS.md` + gel interne samedi 13h30 ; B7 sert de soupape aux idées de dernière minute |
| Départ avec du code non mergé | Merge systématique avant tout départ |

## Après le hackathon

Volontairement bref, car tout a été conçu pour : l'automatisation consiste à
poser `run.py` dans un CronJob Onyxia ou un schedule GitLab CI ; l'ouverture
du code consiste à rendre le dépôt public avec ce document et celui
d'architecture en guise de documentation ; et l'accueil d'un nouvel
utilisateur consiste à dupliquer le doc Grist et créer un salon Tchap — sans
développeur, ce qui était l'objectif de départ.
