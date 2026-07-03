"""Lecture des veilles et écriture des résultats dans Grist (bloc B5).

API REST Grist, pas de client tiers. Idempotence : jamais de réinsertion
d'une paire (uid, veille) existante. Suivi du sort : si le sort d'un uid
déjà en base a changé dans le dump, mettre à jour la ligne et renseigner
la colonne evolution.
"""


def lire_veilles() -> list[dict]:
    """Read active rows from the ``veilles`` table.

    Returns
    -------
    list of dict
        Lignes de veille actives, conformes au contrat.
    """
    msg = "Bloc B5 : à implémenter (voir l'issue du bloc)."
    raise NotImplementedError(msg)


def ecrire_resultats(resultats: list[dict]) -> int:
    """Insert new result rows, skipping existing (uid, veille) pairs.

    Returns
    -------
    int
        Nombre de lignes réellement insérées.
    """
    msg = "Bloc B5 : à implémenter (voir l'issue du bloc)."
    raise NotImplementedError(msg)


def maj_sorts(docs: list[dict]) -> list[dict]:
    """Update the sort of already-stored uids when it changed.

    Returns
    -------
    list of dict
        Les lignes mises à jour (pour la section évolutions du digest).
    """
    msg = "Bloc B5 : à implémenter (voir l'issue du bloc)."
    raise NotImplementedError(msg)
