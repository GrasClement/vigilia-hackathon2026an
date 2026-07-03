"""Extraction et nettoyage des amendements (bloc B2).

Transforme le JSON brut (format Tricoteuses / open data AN) en
"document propre", le contrat d'entrée des matchers. Voir
docs/architecture.md, section Contrats d'interface.
"""

import html
import re

_PARA_BREAK = re.compile(r"</p>\s*<p[^>]*>")
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t]+")


def strip_html(text: str | None) -> str:
    """Decode HTML entities and drop tags, keeping paragraph breaks.

    Parameters
    ----------
    text : str or None
        Raw HTML fragment as found in ``corps.contenuAuteur``. ``None``
        (amendements de suppression sans exposé) is treated as empty.

    Returns
    -------
    str
        Plain UTF-8 text. Paragraph boundaries become newlines,
        non-breaking spaces become regular spaces.

    Examples
    --------
    >>> strip_html("<p>R&#x00E9;tablir cet article&nbsp;:</p><p>Suite</p>")
    'Rétablir cet article :\\nSuite'
    >>> strip_html(None)
    ''
    """
    decoded = html.unescape(text or "")
    decoded = _PARA_BREAK.sub("\n", decoded)
    decoded = _TAG.sub(" ", decoded).replace("\xa0", " ")
    return "\n".join(
        _WS.sub(" ", line).strip() for line in decoded.splitlines()
    ).strip()


def extract_amendement(raw: dict) -> dict:
    """Map a raw amendment JSON to the "document propre" contract.

    Parameters
    ----------
    raw : dict
        Parsed amendment JSON (one file of the Tricoteuses repository).

    Returns
    -------
    dict
        Keys: uid, numero, auteur, texte_ref, place, date_depot, sort,
        url, expose, dispositif. All values are strings.

    Raises
    ------
    ValueError
        If ``raw`` has no ``uid`` — the file is not an amendment.

    Examples
    --------
    >>> doc = extract_amendement({"uid": "AMAN...", "legislature": "17",
    ...     "identification": {"numeroLong": "1"}})
    >>> doc["numero"]
    '1'

    Notes
    -----
    Le chemin du sort après vote reste à confirmer sur un amendement
    adopté ; en attendant, l'état du cycle de vie ("En traitement") sert
    de valeur par défaut. Les dispositifs structurés des amendements de
    crédits ne sont pas gérés (fallback fragmenthtml à ajouter si le cas
    apparaît).
    """
    if "uid" not in raw:
        msg = "Le JSON fourni n'a pas de champ 'uid' : ce n'est pas un amendement."
        raise ValueError(msg)

    corps = raw.get("corps", {}).get("contenuAuteur", {}) or {}
    cycle = raw.get("cycleDeVie", {}) or {}
    division = raw.get("pointeurFragmentTexte", {}).get("division", {}) or {}
    sort = (cycle.get("sort") or {}).get("libelle", "") or (
        cycle.get("etatDesTraitements", {}).get("etat", {}).get("libelle", "")
    )
    legislature = raw.get("legislature", "17")

    return {
        "uid": raw["uid"],
        "numero": raw.get("identification", {}).get("numeroLong", ""),
        "auteur": raw.get("signataires", {}).get("libelle", ""),
        "texte_ref": raw.get("texteLegislatifRef", ""),
        "place": division.get("titre", ""),
        "date_depot": cycle.get("dateDepot", "")[:10],
        "sort": sort,
        "url": f"https://www.assemblee-nationale.fr/dyn/{legislature}/amendements/{raw['uid']}",
        "expose": strip_html(corps.get("exposeSommaire")),
        "dispositif": strip_html(corps.get("dispositif")),
    }
