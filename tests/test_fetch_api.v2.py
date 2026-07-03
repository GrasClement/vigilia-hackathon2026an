"""fetch_api.py

Version avec prise en charge de --date-mode depot|sort|both.
"""

import argparse
import json
from pathlib import Path
from urllib.parse import urlencode

import requests

BASE_URL = "https://parlement.tricoteuses.fr/v2"

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

def build_url(resource, jour, *, search=None, page=1, per_page=100, date_field=None):
    # Choisit le champ de date utilisé pour filtrer la requête.
    field = date_field or DATE_FIELDS.get(resource)
    if field is None:
        raise ValueError(f"Champ de date inconnu pour {resource}")

    params = {
        f"{field}.gte": f"{jour}T00:00:00.000Z",
        f"{field}.lte": f"{jour}T23:59:59.999Z",
        "sort": f"{field}.desc",
        "page": page,
        "perPage": per_page,
    }

    if search:
        params["search"] = search

    return f"{BASE_URL}/{resource}?{urlencode(params)}"


def fetch_jour(resource, jour, *, search=None, per_page=100, date_field=None, timeout=30):
    # Récupère toutes les pages d'une journée.
    items = []
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

        r = requests.get(url, timeout=timeout)
        r.raise_for_status()

        batch = r.json().get("data", [])
        items.extend(batch)

        if len(batch) < per_page:
            break

        page += 1

    return items


def fetch_mots_cles(resource, jour, mots, *, date_field=None):
    # Une requête par mot-clé puis déduplication.
    resultat = {}

    for mot in [m.strip() for m in mots if m.strip()]:
        for item in fetch_jour(resource, jour, search=mot, date_field=date_field):
            uid = item.get("uid") or json.dumps(item, sort_keys=True)
            resultat.setdefault(uid, {**item, "_mots": []})
            resultat[uid]["_mots"].append(mot)

    return list(resultat.values())


def fetch_amendements(jour, *, mots=None, date_mode="depot"):
    """
    date_mode :
      - depot : filtre sur dateDepot
      - sort  : filtre sur dateSort
      - both  : effectue les deux requêtes puis fusionne
    """

    if date_mode == "depot":
        items = (
            fetch_mots_cles("amendements", jour, mots, date_field="dateDepot")
            if mots else
            fetch_jour("amendements", jour, date_field="dateDepot")
        )
        for i in items:
            i["_date_mode"] = ["depot"]
        return items

    if date_mode == "sort":
        items = (
            fetch_mots_cles("amendements", jour, mots, date_field="dateSort")
            if mots else
            fetch_jour("amendements", jour, date_field="dateSort")
        )
        for i in items:
            i["_date_mode"] = ["sort"]
        return items

    # Mode both : fusion des deux listes.
    depot = (
        fetch_mots_cles("amendements", jour, mots, date_field="dateDepot")
        if mots else
        fetch_jour("amendements", jour, date_field="dateDepot")
    )

    sort = (
        fetch_mots_cles("amendements", jour, mots, date_field="dateSort")
        if mots else
        fetch_jour("amendements", jour, date_field="dateSort")
    )

    fusion = {}

    # On ajoute d'abord les amendements trouvés par dateDepot.
    for item in depot:
        uid = item.get("uid") or json.dumps(item, sort_keys=True)
        copie = dict(item)
        copie["_date_mode"] = ["depot"]
        fusion[uid] = copie

    # Puis ceux trouvés par dateSort.
    for item in sort:
        uid = item.get("uid") or json.dumps(item, sort_keys=True)

        if uid in fusion:
            fusion[uid]["_date_mode"].append("sort")
        else:
            copie = dict(item)
            copie["_date_mode"] = ["sort"]
            fusion[uid] = copie

    return list(fusion.values())


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("resource")
    parser.add_argument("--jour", required=True)
    parser.add_argument("--mots", default="")
    parser.add_argument("--date-field")
    parser.add_argument(
        "--date-mode",
        choices=["depot", "sort", "both"],
        default="depot",
        help="Uniquement pour les amendements.",
    )
    parser.add_argument("--out")

    args = parser.parse_args()

    mots = [m.strip() for m in args.mots.split(",") if m.strip()]

    # Cas particulier des amendements.
    if args.resource == "amendements":
        items = fetch_amendements(
            args.jour,
            mots=mots if mots else None,
            date_mode=args.date_mode,
        )
    else:
        if mots:
            items = fetch_mots_cles(
                args.resource,
                args.jour,
                mots,
                date_field=args.date_field,
            )
        else:
            items = fetch_jour(
                args.resource,
                args.jour,
                date_field=args.date_field,
            )

    out = Path(args.out or f"data/{args.resource}_{args.jour}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{len(items)} éléments enregistrés dans {out}")


if __name__ == "__main__":
    main()
