# API Tchap / maubot — publication du digest

Utilisée par `src/veille/digest.py` (bloc B5, fonction `envoyer_tchap`).
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

## Envoi send-only (bloc B5, digest quotidien)

Pas de bot qui écoute pour le digest : une fonction send-only, appelée en
fin de `run.py`, se connecte, poste, se déconnecte. Rien à héberger en
permanence. B5 assemble le message (synthèse de B4 en tête, top 5 par
veille, section évolutions, liens Grist) puis appelle cette fonction —
voir `docs/architecture.md`, bloc B5.

Client : `simplematrixbotlib` (extra `tchap` du projet —
`uv sync --extra tchap`), fonction `send_markdown_message`. Le markdown du
digest (titres, listes, liens) est rendu nativement par Tchap.

```python
import simplematrixbotlib as botlib

creds = botlib.Creds(TCHAP_HOMESERVER, TCHAP_BOT_MATRIX_ID, TCHAP_BOT_PWD)
bot = botlib.Bot(creds)
# send_markdown_message(TCHAP_ROOM_ID, message) puis déconnexion —
# voir digest.py pour l'implémentation exacte du bloc B5.
```

## Fallback mail

Si le compte bot Tchap n'est pas obtenu à temps (seul prérequis du projet
qui dépend d'un tiers), le digest part par mail. L'envoi est isolé
derrière la même fonction d'appel dans `digest.py`, pour que le reste du
pipeline (B1, B1.5, B4) n'ait pas à savoir quel canal est utilisé.

## Extension B7.4 — extension maubot conversationnelle

maubot est réservé à l'extension "mains libres" : un plugin interactif qui
répond aux questions de suivi dans le salon ("qu'est-ce qu'on a détecté
sur ce sujet ce mois-ci ?"). Contrairement à B5 (volontairement
send-only), ce plugin écoute le salon. Il s'appuie sur le mode
conversationnel de B7.3, lui-même construit sur le RAG interne de B7.2
(`docs/api-albert.md`) — jamais sur un service tiers. Réutilise le même
compte bot que B5, mais c'est un complément pull du produit push — jamais
son remplacement, et hors du chemin critique du hackathon (voir
`docs/architecture.md`, bloc B7).
