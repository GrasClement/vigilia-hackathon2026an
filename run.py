"""Pipeline quotidien de veille parlementaire (bloc B9).

Usage :
    uv run run.py               # documents de la veille (j-1)
    uv run run.py --date 2026-07-01

Idempotent : relançable sans doublons (garanti par grist.ecrire_resultats).
L'automatisation consiste à poser ce fichier dans un ordonnanceur externe
(CronJob Onyxia ou schedule de CI) : rien d'autre à écrire.
"""

import argparse
from datetime import date, timedelta

from veille import (
    clean,
    digest,
    fetch,
    grist,
    match_lexical,
    match_meta,
    match_semantique,
)


def main(jour: str) -> None:
    bruts = (
        fetch.fetch_dump()
    )  # option A (fetch_tricoteuses) dès le clone fait, bloc B1
    docs = [clean.extract_amendement(raw) for raw in bruts]
    docs_du_jour = [d for d in docs if d["date_depot"] == jour]

    veilles = grist.lire_veilles()
    resultats = []
    for doc in docs_du_jour:
        for veille in veilles:
            if veille["type"] == "mot_cle":
                hit = match_lexical.match_mot_cle(doc, veille)
            elif veille["type"] in ("parlementaire", "dossier"):
                hit = match_meta.match_metadonnees(doc, veille)
            else:
                hit = None  # les thèmes passent par la collection, plus bas
            if hit:
                resultats.append(hit)

    collection_id = match_semantique.ingest(docs_du_jour, jour)
    for veille in (v for v in veilles if v["type"] == "theme"):
        resultats.extend(match_semantique.match_theme(collection_id, veille))

    inseres = grist.ecrire_resultats(resultats)
    evolutions = grist.maj_sorts(docs)
    message = digest.construire_digest(resultats, evolutions)
    digest.envoyer_tchap(message)
    bilan = f"{jour} : {len(docs_du_jour)} documents, {inseres} alertes"
    print(f"{bilan}, {len(evolutions)} évolutions.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Veille parlementaire quotidienne")
    parser.add_argument(
        "--date",
        default=(date.today() - timedelta(days=1)).isoformat(),
        help="Jour à traiter (YYYY-MM-DD), défaut : hier",
    )
    args = parser.parse_args()
    main(args.date)
