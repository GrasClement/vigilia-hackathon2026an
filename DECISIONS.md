# Journal des décisions

Une ligne par décision, datée. Toute modification d'un contrat d'interface
passe par une synchro d'équipe et s'ajoute ici.

- 2026-07-03 — Source de données : dépôts Git Tricoteuses (JSON éclatés,
  nettoyés, versionnés) ; dump officiel AN codé en fallback, bascule par
  variable d'environnement. Pas de flux temps réel : la promesse est J+1.
- 2026-07-03 — Stockage : Grist = front utilisateur (config, résultats,
  vues) ; la source Git/zip = la donnée ; `data/` local = simple cache.
  Besoin futur → Parquet sur S3 Onyxia (différé).
- 2026-07-03 — Matching : lexical en Python pur pour les mots-clés
  (garantie de rappel), filtres de métadonnées pour parlementaire/dossier,
  recherche hybride Albert pour les thèmes. Le LLM juge complète l'extrait
  cité, ne le remplace jamais.
- 2026-07-03 — Sémantique : une collection Albert par jour, un amendement =
  un document = un chunk (disable_chunking), texte = exposé + dispositif
  tronqué à 8 000 caractères, top-k par veille. Pas de reranker explicite
  tant que l'évaluation n'en montre pas le besoin.
- 2026-07-03 — Notification : compte Tchap dédié (BALF) piloté en send-only
  en fin de pipeline. Pas de serveur bot à héberger. Fallback : mail.
- 2026-07-03 — Orchestration : `run.py` manuel, relançable sans doublons ;
  cron externe (Onyxia / CI) posé uniquement une fois la démo validée.
- 2026-07-03 — Limitation acceptée : les amendements rectifiés
  (numeroRect > 0) ne sont pas re-matchés ; `chronotag` le permettra
  plus tard si besoin.
- 2026-07-03 — Source confirmée : dépôt Tricoteuses
  `assemblee-brut/Amendements_XVII` (git.en-root.org). Schéma AN brut,
  donc les chemins de `clean.py` restent valides tels quels. Clone
  `--depth 1` ; incrémental = `git pull` puis
  `git diff --name-only ORIG_HEAD HEAD`.
- 2026-07-03 — Calendrier recalé sur le programme officiel : code
  14h-23h J1 et 9h45-14h J2 (gel imposé), restitution 3 min à 16h.
  Conséquence : digest v1 exigé J1 soir ; B8 réduit à un backfill ciblé.
- 2026-07-03 — Décision sémantique reconduite après revue
  (disable_chunking, 8 000 caractères, top-k, pas de reranker) ; seule
  retouche : la collection est nommée par run (paramètre), la purge des
  anciennes est reportée après le hackathon.
- 2026-07-03 — Découverte de l'API REST Tricoteuses
  (parlement.tricoteuses.fr/v2) : filtres de date + recherche mot-clé
  côté serveur. Elle devient l'acquisition (fetch_api.py), le clone Git
  et le dump passent en fallbacks. Le search serveur sert de préfiltre ;
  la garantie de rappel et l'extrait restent portés par notre matcher
  lexical local, dont la sémantique est connue. Forme des items à
  confirmer sur le premier jour non vide (enveloppe {"data": [...]}
  vérifiée).
