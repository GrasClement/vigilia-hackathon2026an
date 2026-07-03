"""Acquisition via l'API REST Tricoteuses (bloc B1, option A').

https://parlement.tricoteuses.fr/v2 expose les ressources parlementaires
avec filtre de date et recherche par mot-clé côté serveur. Remplace le
clone Git : une requête par jour (et par mot-clé le cas échéant), rien à
stocker.

Usage en ligne de commande ::

    uv run python -m veille.fetch_api amendements --jour 2026-07-02
    uv run python -m veille.fetch_api questions --jour 2026-07-02 \\
        --mots "budget vert,cour des comptes"
"""

import argparse
import json
from pathlib import Path
from urllib.parse import urlencode

import requests

BASE_URL = "https://parlement.tricoteuses.fr/v2"

#: Champ de date recommandé par ressource (doc API Tricoteuses).
DATE_FIELDS = {
    "amendements": "dateDepot",
    "questions": "dateDepot",
    "documents": "datePublication",
    "dossiers": "dateDernierActe",
    "actesLegislatifs": "dateActe",
    "etapesLegislatives": "dateDebut",
    "scrutins": "dateScrutin",
    "reunions": "dateSeance",
    "debats": "dateSeance",
    "interventions": "dateSeance",
}


def build_url(
    resource: str,
    jour: str,
    *,
    search: str | None = None,
    page: int = 1,
    per_page: int = 100,
    date_field: str | None = None,
) -> str:
    """Build one API request URL for a resource on a given day.

    Parameters
    ----------
    resource : str
        API resource name (``amendements``, ``questions``, ...). Must be
        a key of ``DATE_FIELDS`` unless ``date_field`` is given.
    jour : str
        Day to fetch, ISO format ``YYYY-MM-DD``.
    search : str or None, default=None
        Keyword or phrase for server-side full-text search.
    page : int, default=1
        Page number (1-based).
    per_page : int, default=100
        Page size.
    date_field : str or None, default=None
        Override the recommended date field (e.g. ``dateSort`` to watch
        amendment outcomes instead of deposits).

    Returns
    -------
    str
        Full request URL, query string encoded.

    Raises
    ------
    ValueError
        If ``resource`` has no known date field and none is provided,
        or if ``jour`` is not ``YYYY-MM-DD``.

    Examples
    --------
    >>> build_url("amendements", "2026-07-02", search="budget", per_page=10)
    'https://parlement.tricoteuses.fr/v2/amendements?dateDepot.gte=2026-07-02T00%3A00%3A00.000Z&dateDepot.lte=2026-07-02T23%3A59%3A59.999Z&sort=dateDepot.desc&page=1&perPage=10&search=budget'
    """
    field = date_field or DATE_FIELDS.get(resource)
    if field is None:
        msg = (
            f"Pas de champ de date connu pour '{resource}'. "
            f"Ressources connues : {sorted(DATE_FIELDS)}, "
            "ou passer date_field explicitement."
        )
        raise ValueError(msg)
    if len(jour) != 10 or jour[4] != "-" or jour[7] != "-":
        msg = f"jour doit être au format YYYY-MM-DD, reçu : {jour!r}"
        raise ValueError(msg)

    params: dict[str, str | int] = {
        f"{field}.gte": f"{jour}T00:00:00.000Z",
        f"{field}.lte": f"{jour}T23:59:59.999Z",
        "sort": f"{field}.desc",
        "page": page,
        "perPage": per_page,
    }
    if search:
        params["search"] = search
    return f"{BASE_URL}/{resource}?{urlencode(params)}"


def fetch_jour(
    resource: str,
    jour: str,
    *,
    search: str | None = None,
    per_page: int = 100,
    date_field: str | None = None,
    timeout: int = 30,
) -> list[dict]:
    """Fetch all items of a resource for one day, paginating as needed.

    Parameters
    ----------
    resource : str
        API resource name (see ``DATE_FIELDS``).
    jour : str
        Day to fetch, ``YYYY-MM-DD``.
    search : str or None, default=None
        Optional server-side keyword search.
    per_page : int, default=100
        Page size; pagination stops when a page comes back short.
    date_field : str or None, default=None
        Override the recommended date field.
    timeout : int, default=30
        Per-request timeout in seconds.

    Returns
    -------
    list of dict
        All items of the day (the ``data`` arrays, concatenated).

    Raises
    ------
    requests.HTTPError
        If a request fails.
    """
    items: list[dict] = []
    page = 1
    while True:
        url = build_url(
            resource,
            jour,
            search=search,
            page=page,
            per_page=per_page,
            date_field=date_field,
        )
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        batch = response.json().get("data", [])
        items.extend(batch)
        if len(batch) < per_page:
            return items
        page += 1


def fetch_mots_cles(
    resource: str,
    jour: str,
    mots: list[str],
    *,
    date_field: str | None = None,
) -> list[dict]:
    """Fetch one day filtered by keywords, deduplicated across keywords.

    One request per keyword (server-side search) ; chaque item porte en
    sortie la liste des mots-clés qui l'ont remonté dans ``_mots``.

    Parameters
    ----------
    resource : str
        API resource name.
    jour : str
        Day to fetch, ``YYYY-MM-DD``.
    mots : list of str
        Keywords or phrases; empty strings are ignored.
    date_field : str or None, default=None
        Override the recommended date field.

    Returns
    -------
    list of dict
        Deduplicated items (by ``uid``, fallback to the whole payload),
        each with an added ``_mots`` key.

    Raises
    ------
    ValueError
        If ``mots`` contains no usable keyword.
    """
    mots_utiles = [m.strip() for m in mots if m.strip()]
    if not mots_utiles:
        msg = "Aucun mot-clé exploitable dans 'mots'."
        raise ValueError(msg)

    par_uid: dict[str, dict] = {}
    for mot in mots_utiles:
        for item in fetch_jour(resource, jour, search=mot, date_field=date_field):
            cle = item.get("uid") or json.dumps(item, sort_keys=True)
            par_uid.setdefault(cle, {**item, "_mots": []})
            par_uid[cle]["_mots"].append(mot)
    return list(par_uid.values())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extraction Tricoteuses par jour, avec mots-clés optionnels"
    )
    parser.add_argument("resource", help=f"Ressource API : {sorted(DATE_FIELDS)}")
    parser.add_argument("--jour", required=True, help="Jour YYYY-MM-DD")
    parser.add_argument(
        "--mots", default="", help="Mots-clés séparés par des virgules (optionnel)"
    )
    parser.add_argument(
        "--date-field", default=None, help="Champ de date alternatif (ex. dateSort)"
    )
    parser.add_argument(
        "--out", default=None, help="Fichier JSON de sortie (défaut : data/...)"
    )
    args = parser.parse_args()

    mots = [m for m in args.mots.split(",") if m.strip()]
    if mots:
        items = fetch_mots_cles(
            args.resource, args.jour, mots, date_field=args.date_field
        )
    else:
        items = fetch_jour(args.resource, args.jour, date_field=args.date_field)

    out = Path(args.out or f"data/{args.resource}_{args.jour}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(items, ensure_ascii=False, indent=1))
    print(f"{args.resource} {args.jour} : {len(items)} items -> {out}")


if __name__ == "__main__":
    main()
