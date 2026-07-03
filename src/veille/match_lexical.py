"""Matching lexical des veilles mot_cle (bloc B3).

Contrat : déterministe et garanti — un mot-clé présent déclenche
toujours ; un terme d'exclusion présent annule le match. Sortie : lignes
de résultat (voir docs/architecture.md), score 100, methode "lexical",
extrait = la phrase contenant le terme.
"""


def match_mot_cle(doc: dict, veille: dict) -> dict | None:
    """Match one document against one mot_cle veille.

    Parameters
    ----------
    doc : dict
        Document propre (sortie de clean.extract_amendement).
    veille : dict
        Ligne de la table Grist ``veilles`` avec type == "mot_cle".

    Returns
    -------
    dict or None
        Ligne de résultat si match, sinon None.
    """
    msg = "Bloc B3 : à implémenter (voir l'issue du bloc)."
    raise NotImplementedError(msg)
