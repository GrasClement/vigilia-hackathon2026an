"""Matching sémantique des veilles theme via Albert API (bloc B4).

Une collection par run (nommée par paramètre : date ou label — le
backfill de B8 en a besoin ; purge des anciennes reportée), un
amendement = un document = un chunk (disable_chunking), texte = exposé +
dispositif tronqué à config.EMBED_MAX_CHARS, metadata = {uid, texte_ref,
date_depot}. Recherche POST /v1/search, method=hybrid, top-k par veille.
Quotas (offre Expérimentation) : embeddings 500/min et 50 000/jour,
chat 1 000/jour — le LLM juge (niveau 2+) reste sur le top-k.
"""


def ingest(docs: list[dict], label: str) -> str:
    """Create the run's collection and upload new documents.

    Returns
    -------
    str
        The collection id.
    """
    msg = "Bloc B4 : à implémenter (voir l'issue du bloc)."
    raise NotImplementedError(msg)


def match_theme(collection_id: str, veille: dict) -> list[dict]:
    """Search the daily collection with one theme veille.

    Returns
    -------
    list of dict
        Lignes de résultat du top-k, score renormalisé 0-100,
        methode "semantique", extrait = le chunk retourné.
    """
    msg = "Bloc B4 : à implémenter (voir l'issue du bloc)."
    raise NotImplementedError(msg)
