#%%
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


# Ton notebook est dans notebooks/, donc on remonte d'un niveau
ROOT_DIR = Path("../data/tricoteuses_amendements")


def normaliser_date(date: str) -> str:
    """
    Accepte :
    - '01/04/2025'
    - '2025-04-01'

    Renvoie toujours :
    - '2025-04-01'
    """
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date, fmt).date().isoformat()
        except ValueError:
            pass

    raise ValueError(
        "Date invalide. Utilise par exemple '01/04/2025' ou '2025-04-01'."
    )


def filtrer_amendements_par_date(
    date_recherchee: str,
    root_dir: Path = ROOT_DIR,
) -> list[dict]:
    """
    Renvoie tous les JSON dont datePublication correspond exactement
    au jour demandé.

    Chaque élément contient :
    - chemin : chemin local du JSON
    - fichier : nom du fichier
    - data : contenu complet du JSON
    """
    date_cible = normaliser_date(date_recherchee)

    if not root_dir.exists():
        raise FileNotFoundError(
            f"Dossier introuvable : {root_dir.resolve()}"
        )

    resultats = []
    erreurs = []

    for fichier in root_dir.rglob("*.json"):
        try:
            with fichier.open("r", encoding="utf-8-sig") as f:
                data = json.load(f)

            # Exemple attendu :
            # "2025-04-01T00:00:00+02:00"
            date_publication = data.get("datePublication")

            if not isinstance(date_publication, str):
                continue

            # On garde seulement AAAA-MM-JJ
            date_json = date_publication[:10]

            if date_json == date_cible:
                resultats.append(
                    {
                        "chemin": fichier,
                        "fichier": fichier.name,
                        "datePublication": date_publication,
                        "data": data,
                    }
                )

        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as erreur:
            erreurs.append(
                {
                    "fichier": str(fichier),
                    "erreur": str(erreur),
                }
            )

    print(f"{len(resultats)} amendement(s) publié(s) le {date_cible}.")

    if erreurs:
        print(f"{len(erreurs)} fichier(s) ignoré(s) à cause d'une erreur.")

    return resultats


#%%
#%%
amendements_1_avril = filtrer_amendements_par_date("01/04/2025")
# %%
