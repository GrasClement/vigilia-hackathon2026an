"""
fetch_api.py — version corrigée

Ajouts :
- --date-mode depot | sort | both
- robustesse API (data/results/items)
- pagination safe
- déduplication propre
- correction mode both
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


# ---------------------------
# BUILD URL
# ---------------------------
def build_url(resource, jour, *, search=None, page=1, per_page=100, date_field=None):
    field = date_field or DATE_FIELDS.get(resource)

    if not field:
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


# ---------------------------
# FETCH PAGINATED DAY
# ---------------------------
def fetch_jour(resource, jour, *, search=None, per_page=100, date_field=None, timeout=30):
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

        data = r.json()

        # API parfois incohérente → fallback robuste
        batch = data.get("data") or data.get("results") or data.get("items") or []

        if not batch:
            break

        items.extend(batch)

        # dernière page détectée
        if len(batch) < per_page:
            break

        page += 1

    return items


# ---------------------------
# SEARCH KEYWORDS + DEDUP
# ---------------------------
def fetch_mots_cles(resource, jour, mots, *, date_field=None):
    mots = [m.strip() for m in mots if m.strip()]
    if not mots:
        raise ValueError("Aucun mot-clé valide")

    result = {}

    for mot in mots:
        for item in fetch_jour(resource, jour, search=mot, date_field=date_field):
            uid = item.get("uid") or json.dumps(item, sort_keys=True)

            if uid not in result:
                result[uid] = {**item, "_mots": []}

            result[uid]["_mots"].append(mot)

    return list(result.values())


# ---------------------------
# AMENDEMENTS SPECIAL MODE
# ---------------------------
def fetch_amendements(jour, *, mots=None, date_mode="depot"):
    def run(date_field):
        if mots:
            return fetch_mots_cles("amendements", jour, mots, date_field=date_field)
        return fetch_jour("amendements", jour, date_field=date_field)

    # ---- DEPOT ONLY
    if date_mode == "depot":
        items = run("dateDepot")
        for i in items:
            i["_date_mode"] = ["depot"]
        return items

    # ---- SORT ONLY
    if date_mode == "sort":
        items = run("dateSort")
        for i in items:
            i["_date_mode"] = ["sort"]
        return items

    # ---- BOTH
    depot = run("dateDepot")
    sort = run("dateSort")

    fusion = {}

    # dépôt
    for item in depot:
        uid = item.get("uid") or json.dumps(item, sort_keys=True)
        item = dict(item)
        item["_date_mode"] = ["depot"]
        fusion[uid] = item

    # sort
    for item in sort:
        uid = item.get("uid") or json.dumps(item, sort_keys=True)

        if uid in fusion:
            if "sort" not in fusion[uid]["_date_mode"]:
                fusion[uid]["_date_mode"].append("sort")
        else:
            item = dict(item)
            item["_date_mode"] = ["sort"]
            fusion[uid] = item

    return list(fusion.values())


# ---------------------------
# CLI
# ---------------------------
def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("resource")
    parser.add_argument("--jour", required=True)
    parser.add_argument("--mots", default="")

    parser.add_argument("--date-field", default=None)

    parser.add_argument(
        "--date-mode",
        choices=["depot", "sort", "both"],
        default="depot",
    )

    parser.add_argument("--out", default=None)

    args = parser.parse_args()

    mots = [m.strip() for m in args.mots.split(",") if m.strip()]

    # ---- AMENDEMENTS
    if args.resource == "amendements":
        items = fetch_amendements(
            args.jour,
            mots=mots if mots else None,
            date_mode=args.date_mode,
        )

    # ---- AUTRES RESSOURCES
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

    # ---- OUTPUT
    out = Path(args.out or f"data/{args.resource}_{args.jour}.json")
    out.parent.mkdir(parents=True, exist_ok=True)

    out.write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"OK → {len(items)} items écrits dans {out}")


if __name__ == "__main__":
    main()
