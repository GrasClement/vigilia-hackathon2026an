"""Matching par métadonnées des veilles parlementaire / dossier (bloc B3).

Égalité souple (casse, espaces) sur le champ auteur (cosignataires
inclus, le libellé complet les contient) ou texte_ref. Score 100,
methode "metadonnees", extrait = le champ matché.
"""


def match_metadonnees(doc: dict, veille: dict) -> dict | None:
    """Match one document against one parlementaire/dossier veille.

    Parameters
    ----------
    doc : dict
        Document propre.
    veille : dict
        Ligne de veille avec type in {"parlementaire", "dossier"}.

    Returns
    -------
    dict or None
        Ligne de résultat si match, sinon None.
    """
    msg = "Bloc B3 : à implémenter (voir l'issue du bloc)."
    raise NotImplementedError(msg)
