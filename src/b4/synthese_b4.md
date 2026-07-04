# B4 — Génération du message de veille (brique `synthese.py`)

Ce que fait la brique, pourquoi elle est construite ainsi, et ce qu'elle
garantit au reste du pipeline. Module : `src/veille/synthese.py`. Détail
des endpoints : `docs/api-albert.md`.

## Rôle

B4 transforme le résultat quotidien d'**une** veille (les lignes Grist du
jour) en **message Tchap complet** en markdown : synthèse rédigée,
chiffres clés, priorités, amendements à ouvrir avec liens. B5 ne fait
plus que l'envoyer. C'est un changement de périmètre acté par la spec B2
(voir `DECISIONS.md`) : l'ancienne version où B4 ne produisait qu'un
paragraphe et B5 assemblait le digest est abandonnée.

## Principe directeur : le LLM rédige, il ne calcule pas

Tout ce qui est comptage, jugement ou sélection est fait en Python,
avant l'appel. Le modèle reçoit des résultats, pas des tâches :

| Responsabilité | Où | Comment |
|---|---|---|
| Chiffres (total, répartitions) | Python | `construire_stats` — Counter sur les colonnes Grist ; le prompt interdit au LLM tout chiffre hors de ce JSON |
| Ordre de pertinence | Albert `/v1/rerank` | query = `objectif` (repli `veille_termes`) contre les exposés sommaires ; repli déterministe : tri `dateDepot` décroissante |
| Niveaux Forte/Moyenne/Faible | Python | `niveau_priorite` — Forte : sort notable ou député suivi ; Moyenne : filtres multiples ; Faible : le reste. Le LLM les recopie, ne les rejuge pas |
| Sélection cas déluge | Python | K = 25 amendements en texte intégral (les mieux classés), le reste en une ligne, stats sur la totalité |
| URLs | Python | `url_amendement(uid)` — le prompt interdit au LLM de construire une URL |
| Rédaction | Albert chat | Mistral-Small, temp 0.2, gabarit strict dans le prompt système |

Ce partage préserve l'explicabilité (une priorité "Forte" se justifie par
une colonne, pas par un score opaque) et rend chaque étape testable sans
réseau.

## Contrat

```python
generer_message(contexte: dict, amendements: list[dict], *,
                k: int = 25, modele: str = MODELE_CHAT) -> str
```

- `contexte` : la ligne de veille (`veille_nom`, `objectif`,
  `veille_termes`, `veille_noms`, ...).
- `amendements` : les lignes Grist du jour pour cette veille, schéma de
  la table `resultats` (voir `docs/architecture.md`) — textes complets
  (`dispositif`, `exposeSommaire`) inclus.
- Retour : **une chaîne jamais vide.** Trois sorties possibles :
  1. le message rédigé par Albert (cas nominal) ;
  2. `"Aucun amendement détecté aujourd'hui pour cette veille."` si la
     liste est vide — aucun appel API ;
  3. le **message de secours** si l'appel chat échoue : bandeau
     d'avertissement explicite ("la synthèse automatique a échoué"),
     chiffres clés issus des stats Python, top 5 avec liens. Le digest
     part toujours, et son lecteur sait qu'il lit un mode dégradé.
- La fonction ne lève jamais, à une exception près : `ALBERT_API_KEY`
  absente de l'environnement (erreur de déploiement, pas d'exécution —
  elle doit faire échouer le run bruyamment).

## Garanties anti-hallucination

Deux mécanismes, dans le prompt système :

1. **Chiffres** : uniquement depuis le JSON de statistiques. Interdiction
   de compter, recalculer, ou produire un pourcentage absent du JSON.
2. **Faits** : uniquement depuis les textes fournis (dispositif, exposé
   sommaire, métadonnées). L'objectif de veille est une grille de
   lecture, jamais une source factuelle.

Et un mécanisme structurel : le prompt annonce que les stats portent sur
N amendements dont seuls K sont fournis en texte intégral, ce qui
empêche le modèle de présenter les prioritaires comme l'exhaustivité.

## Budget réseau et tokens

2 appels par veille par jour. Payload chat en cas déluge : ~20 k tokens
(K = 25 × ~600 tokens + stats + consignes), loin des 128 k TPM. Sortie
plafonnée à 2 500 tokens (le message complet en consomme 800–1 000).

## Tests

`tests/test_synthese.py`, aucun réseau réel (sessions mockées) : niveaux
de priorité par branche, stats, jointure par `index` du rerank, exclusion
des exposés vides du batch, repli par date, message de secours, cas zéro
amendement, assemblage du prompt (trois blocs, annonce du plafond).

## À vérifier au premier run réel

- [ ] Format d'URL `/dyn/17/amendements/{uid}` : cliquer un lien du
      message généré.
- [ ] Valeurs réelles de `sortAmendement` contre `SORTS_NOTABLES`
      (adopté, rejeté, retiré, irrecevable, tombé) — compléter si l'API
      renvoie d'autres libellés.
- [ ] Qualité de la synthèse sur un cas déluge réel ; si insuffisante,
      A/B avec `gpt-oss-120b` (une ligne de config).