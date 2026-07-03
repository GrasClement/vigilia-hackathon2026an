# API Tchap / maubot — diffusion du digest

Utilisée par `src/veille/digest.py` (bloc B2, fonction `envoyer_tchap`).
Tchap est la messagerie souveraine de l'État (fédération Matrix fermée aux
agents publics).

## Compte bot dédié

Un compte Tchap dédié, adossé à une BALF (boîte aux lettres fonctionnelle),
procédure documentée par la communauté Tchap et le retour d'expérience
SSPhub — voir la décision "Notification" dans `docs/architecture.md`.
Variables d'environnement (`.env.example`) :

```
TCHAP_HOMESERVER=
TCHAP_BOT_MATRIX_ID=
TCHAP_BOT_PWD=
TCHAP_ROOM_ID=
```

Le bot doit être invité dans le salon de diffusion (`TCHAP_ROOM_ID`) avant
le premier envoi.

## Envoi send-only (digest quotidien)

Pas de bot qui écoute pour le digest : une fonction send-only, appelée en
fin de `run.py`, se connecte, poste, se déconnecte. Rien à héberger en
permanence.

Client : `simplematrixbotlib` (extra `tchap` du projet —
`uv sync --extra tchap`), fonction `send_markdown_message`. Le markdown du
digest (titres, listes, liens) est rendu nativement par Tchap.

```python
import simplematrixbotlib as botlib

creds = botlib.Creds(TCHAP_HOMESERVER, TCHAP_BOT_MATRIX_ID, TCHAP_BOT_PWD)
bot = botlib.Bot(creds)
# send_markdown_message(TCHAP_ROOM_ID, message) puis déconnexion —
# voir digest.py pour l'implémentation exacte du bloc B2.
```

## Fallback mail

Si le compte bot Tchap n'est pas obtenu à temps (seul prérequis du projet
qui dépend d'un tiers), le digest part par mail. L'envoi est isolé
derrière la même fonction d'appel dans `digest.py`, pour que le reste du
pipeline (B1, B4) n'ait pas à savoir quel canal est utilisé.

## Extension — agent de consultation (bloc B6.3)

maubot est réservé à l'extension "mains libres" : un plugin interactif qui
répond aux questions de suivi dans le salon ("où en est ce texte ? qui est
l'auteur ?") en s'appuyant sur le serveur MCP Parlement de Tricoteuses.
Réutilise le même compte bot que le digest, mais c'est un complément pull
du produit push — jamais son remplacement, et hors du chemin critique du
hackathon (voir `docs/architecture.md`, bloc B6).
