"""
Acquisition via l'API REST Tricoteuses.

L'API https://parlement.tricoteuses.fr/v2 expose des ressources
parlementaires filtrables par période et par mot-clé côté serveur.

Exemples CLI
------------
Une seule journée :
    uv run python -m veille.fetch_api amendements --date-debut 2026-07-02

Une période :
    uv run python -m veille.fetch_api amendements \
        --date-debut 2026-07-01 \
        --date-fin 2026-07-03 \
        --mots "budget"

Plusieurs mots-clés :
    uv run python -m veille.fetch_api questions \
        --date-debut 2026-07-01 \
        --date-fin 2026-07-03 \
        --mots "budget vert,cour des comptes"

Compatibilité avec l'ancien argument :
    uv run python -m veille.fetch_api amendements --jour 2026-07-02
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

import requests


BASE_URL = "https://parlement.tricoteuses.fr/v2"


#: Champ de date recommandé selon la ressource Tricoteuses.
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


def _valider_periode(
    date_debut: str,
    date_fin: str | None = None,
) -> tuple[str, str]:
    """
    Vérifie que les dates sont au format YYYY-MM-DD et que la période est valide.

    Si date_fin est absente, la période correspond à une seule journée.
    """
    date_fin = date_fin or date_debut

    try:
        debut = date.fromisoformat(date_debut)
        fin = date.fromisoformat(date_fin)
    except ValueError as exc:
        raise ValueError(
            "date_debut et date_fin doivent être au format YYYY-MM-DD."
        ) from exc

    if fin < debut:
        raise ValueError(
            f"date_fin ({date_fin}) ne peut pas être antérieure "
            f"à date_debut ({date_debut})."
        )

    return debut.isoformat(), fin.isoformat()


def build_url(
    resource: str,
    date_debut: str,
    date_fin: str | None = None,
    *,
    search: str | None = None,
    page: int = 1,
    per_page: int = 100,
    date_field: str | None = None,
) -> str:
    """
    Construit une URL API Tricoteuses pour une période donnée.

    Parameters
    ----------
    resource : str
        Nom de la ressource API, par exemple ``amendements``.
    date_debut : str
        Date de début incluse, au format YYYY-MM-DD.
    date_fin : str | None
        Date de fin incluse, au format YYYY-MM-DD.
        Si absente : même valeur que ``date_debut``.
    search : str | None
        Mot-clé ou expression recherchée côté serveur.
    page : int
        Numéro de page, en commençant à 1.
    per_page : int
        Nombre d'éléments par page.
    date_field : str | None
        Champ de date alternatif. Par exemple ``dateSort`` pour les
        amendements si tu veux suivre leur sort plutôt que leur dépôt.

    Returns
    -------
    str
        URL complète de requête.

    Examples
    --------
    >>> build_url(
    ...     "amendements",
    ...     "2026-07-01",
    ...     "2026-07-03",
    ...     search="budget",
    ...     per_page=10,
    ... )
    'https://parlement.tricoteuses.fr/v2/amendements?dateDepot.gte=2026-07-01T00:00:00.000Z&dateDepot.lte=2026-07-03T23:59:59.999Z&sort=dateDepot.desc&search=budget&page=1&perPage=10'
    """
    field = date_field or DATE_FIELDS.get(resource)

    if field is None:
        raise ValueError(
            f"Pas de champ de date connu pour '{resource}'. "
            f"Ressources connues : {sorted(DATE_FIELDS)}. "
            "Tu peux aussi préciser date_field explicitement."
        )

    if page < 1:
        raise ValueError("page doit être supérieur ou égal à 1.")

    if per_page < 1:
        raise ValueError("per_page doit être supérieur ou égal à 1.")

    date_debut, date_fin = _valider_periode(date_debut, date_fin)

    # Liste de tuples pour contrôler l'ordre final des paramètres.
    params = [
        (f"{field}.gte", f"{date_debut}T00:00:00.000Z"),
        (f"{field}.lte", f"{date_fin}T23:59:59.999Z"),
        ("sort", f"{field}.desc"),
    ]

    if search:
        params.append(("search", search))

    params.extend(
        [
            ("page", page),
            ("perPage", per_page),
        ]
    )

    # safe=":" garde les heures lisibles dans l'URL. Peut être à enlever #TODO
    query = urlencode(params, safe=":")

    return f"{BASE_URL}/{resource}?{query}"


def fetch_periode(
    resource: str,
    date_debut: str,
    date_fin: str | None = None,
    *,
    search: str | None = None,
    per_page: int = 100,
    date_field: str | None = None,
    timeout: int = 30,
) -> list[dict]:
    """
    Récupère tous les éléments d'une ressource sur une période.

    La fonction gère automatiquement la pagination : elle continue tant
    qu'une page contient exactement ``per_page`` résultats.
    """
    items: list[dict] = []
    page = 1

    while True:
        url = build_url(
            resource=resource,
            date_debut=date_debut,
            date_fin=date_fin,
            search=search,
            page=page,
            per_page=per_page,
            date_field=date_field,
        )

        response = requests.get(url, timeout=timeout)
        response.raise_for_status()

        payload = response.json()
        batch = payload.get("data", [])

        if not isinstance(batch, list):
            raise ValueError(
                "Réponse API inattendue : la clé 'data' ne contient pas une liste."
            )

        items.extend(batch)

        if len(batch) < per_page:
            break

        page += 1

    return items


def fetch_jour(
    resource: str,
    jour: str,
    *,
    search: str | None = None,
    per_page: int = 100,
    date_field: str | None = None,
    timeout: int = 30,
) -> list[dict]:
    """
    Récupère une seule journée.

    C'est un alias de ``fetch_periode`` conservé pour ne pas casser
    tes scripts existants.
    """
    return fetch_periode(
        resource=resource,
        date_debut=jour,
        date_fin=jour,
        search=search,
        per_page=per_page,
        date_field=date_field,
        timeout=timeout,
    )


def fetch_mots_cles(
    resource: str,
    date_debut: str,
    mots: list[str],
    *,
    date_fin: str | None = None,
    per_page: int = 100,
    date_field: str | None = None,
    timeout: int = 30,
) -> list[dict]:
    """
    Récupère une période pour plusieurs mots-clés, avec dédoublonnage.

    Chaque item retourne une colonne ``_mots`` contenant le ou les mots-clés
    qui l'ont fait remonter.
    """
    mots_utiles = [mot.strip() for mot in mots if mot.strip()]

    if not mots_utiles:
        raise ValueError("Aucun mot-clé exploitable dans 'mots'.")

    par_uid: dict[str, dict] = {}

    for mot in mots_utiles:
        items_mot = fetch_periode(
            resource=resource,
            date_debut=date_debut,
            date_fin=date_fin,
            search=mot,
            per_page=per_page,
            date_field=date_field,
            timeout=timeout,
        )

        for item in items_mot:
            cle = item.get("uid") or json.dumps(item, ensure_ascii=False, sort_keys=True)

            if cle not in par_uid:
                par_uid[cle] = {
                    **item,
                    "_mots": [],
                }

            par_uid[cle]["_mots"].append(mot)

    return list(par_uid.values())


def main() -> None:
    """Point d'entrée pour l'utilisation en ligne de commande."""
    parser = argparse.ArgumentParser(
        description="Extraction Tricoteuses par période, avec mots-clés optionnels."
    )

    parser.add_argument(
        "resource",
        help=f"Ressource API. Exemples : {', '.join(sorted(DATE_FIELDS))}",
    )

    parser.add_argument(
        "--date-debut",
        "--jour",
        dest="date_debut",
        required=True,
        help="Date de début au format YYYY-MM-DD.",
    )

    parser.add_argument(
        "--date-fin",
        default=None,
        help="Date de fin au format YYYY-MM-DD. Défaut : même jour que date-debut.",
    )

    parser.add_argument(
        "--mots",
        default="",
        help="Mots-clés séparés par des virgules. Exemple : 'budget,cour des comptes'.",
    )

    parser.add_argument(
        "--date-field",
        default=None,
        help="Champ de date alternatif. Exemple : dateSort.",
    )

    parser.add_argument(
        "--per-page",
        type=int,
        default=100,
        help="Nombre de résultats par page API. Défaut : 100.",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout HTTP par requête, en secondes. Défaut : 30.",
    )

    parser.add_argument(
        "--out",
        default=None,
        help="Chemin du JSON de sortie. Défaut : data/<ressource>_<debut>_<fin>.json",
    )

    args = parser.parse_args()

    mots = [mot.strip() for mot in args.mots.split(",") if mot.strip()]

    if mots:
        items = fetch_mots_cles(
            resource=args.resource,
            date_debut=args.date_debut,
            date_fin=args.date_fin,
            mots=mots,
            per_page=args.per_page,
            date_field=args.date_field,
            timeout=args.timeout,
        )
    else:
        items = fetch_periode(
            resource=args.resource,
            date_debut=args.date_debut,
            date_fin=args.date_fin,
            per_page=args.per_page,
            date_field=args.date_field,
            timeout=args.timeout,
        )

    date_fin_sortie = args.date_fin or args.date_debut

    out = Path(
        args.out
        or f"data/{args.resource}_{args.date_debut}_{date_fin_sortie}.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)

    out.write_text(
        json.dumps(items, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )

    print(
        f"{args.resource} | {args.date_debut} -> {date_fin_sortie} "
        f"| {len(items)} items -> {out}"
    )


if __name__ == "__main__":
    main()
