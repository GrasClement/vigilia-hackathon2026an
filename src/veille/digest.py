"""Digest quotidien envoyé sur Tchap (bloc B6).

Agrégation par texte législatif, top 5 par veille au format
"titre + deux lignes + lien", section évolutions (sorts changés), lien
vers la vue Grist filtrée. Envoi send-only via un compte Tchap dédié
(simplematrixbotlib) : pas de bot qui écoute, pas de serveur à héberger.
"""


def construire_digest(resultats: list[dict], evolutions: list[dict]) -> str:
    """Build the daily digest as a Markdown string.

    Returns
    -------
    str
        Markdown, rendu nativement par Tchap. Lisible en 30 secondes.
    """
    msg = "Bloc B6 : à implémenter (voir l'issue du bloc)."
    raise NotImplementedError(msg)


def envoyer_tchap(message: str) -> None:
    """Send one Markdown message to the diffusion room and disconnect.

    Notes
    -----
    Nécessite l'extra ``tchap`` (``uv sync --extra tchap``) et les
    variables TCHAP_* du .env. S'appuie sur simplematrixbotlib
    (send_markdown_message) avec le compte dédié.
    """
    msg = "Bloc B6 : à implémenter (voir l'issue du bloc)."
    raise NotImplementedError(msg)
