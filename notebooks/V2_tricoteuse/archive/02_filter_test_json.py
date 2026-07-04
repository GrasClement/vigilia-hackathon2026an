#%%
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path

import polars as pl



#%%
print(Path.cwd())
#%%
# ---------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------

# Dossier local contenant tous les amendements déjà téléchargés
ROOT_DIR = Path("../data/tricoteuses_amendements")

# Exemple : un dossier PION... présent dans ROOT_DIR
SOUS_DOSSIER_TEST = "PIONANR5L17B0104"

# Affiche le détail des N premiers fichiers seulement
N_AFFICHAGE_MAX = 30


#%%
# ---------------------------------------------------------------------
# FONCTIONS DE LECTURE
# ---------------------------------------------------------------------

def trouver_valeur(obj, cle: str):
    """
    Cherche récursivement une clé dans un JSON.
    Fonctionne même si datePublication n'est pas à la racine.
    """
    if isinstance(obj, dict):
        if cle in obj:
            return obj[cle]

        for valeur in obj.values():
            resultat = trouver_valeur(valeur, cle)

            if resultat is not None:
                return resultat

    elif isinstance(obj, list):
        for valeur in obj:
            resultat = trouver_valeur(valeur, cle)

            if resultat is not None:
                return resultat

    return None


def parser_date_publication(date_brute: str) -> datetime:
    """
    Transforme par exemple :
    2025-04-01T00:00:00+02:00

    en objet datetime Python.
    """
    return datetime.fromisoformat(date_brute.replace("Z", "+00:00"))


#%%
# ---------------------------------------------------------------------
# VERIFICATION DU DOSSIER LOCAL
# ---------------------------------------------------------------------

dossier_test = ROOT_DIR / SOUS_DOSSIER_TEST

if not ROOT_DIR.exists():
    raise FileNotFoundError(
        f"Le dossier racine n'existe pas : {ROOT_DIR.resolve()}"
    )

if not dossier_test.exists():
    dossiers_disponibles = sorted(
        p.name
        for p in ROOT_DIR.iterdir()
        if p.is_dir()
    )

    print("Exemples de dossiers disponibles :")
    print(dossiers_disponibles[:20])

    raise FileNotFoundError(
        f"Le sous-dossier {SOUS_DOSSIER_TEST} n'existe pas dans "
        f"{ROOT_DIR.resolve()}"
    )


#%%
# ---------------------------------------------------------------------
# LECTURE DES JSON DU SOUS-DOSSIER
# ---------------------------------------------------------------------

fichiers_json = sorted(dossier_test.rglob("*.json"))

print(f"Dossier analysé : {dossier_test.resolve()}")
print(f"Nombre de JSON trouvés : {len(fichiers_json)}")


#%%
# ---------------------------------------------------------------------
# EXTRACTION ET AFFICHAGE DES DATES
# ---------------------------------------------------------------------

lignes = []

for i, fichier in enumerate(fichiers_json, start=1):
    try:
        with fichier.open("r", encoding="utf-8-sig") as f:
            amendement = json.load(f)

        date_brute = trouver_valeur(amendement, "datePublication")
        uid = trouver_valeur(amendement, "uid")
        numero_long = trouver_valeur(amendement, "numeroLong")
        date_depot = trouver_valeur(amendement, "dateDepot")

        if date_brute is not None:
            date_parsee = parser_date_publication(date_brute)

            date_iso = date_parsee.date().isoformat()
            heure = date_parsee.time().isoformat()
            fuseau = str(date_parsee.tzinfo)

        else:
            date_iso = None
            heure = None
            fuseau = None

        lignes.append(
            {
                "fichier": fichier.name,
                "chemin": str(fichier),
                "datePublication_brute": date_brute,
                "datePublication_date": date_iso,
                "datePublication_heure": heure,
                "datePublication_fuseau": fuseau,
                "dateDepot": date_depot,
                "uid": uid,
                "numeroLong": numero_long,
                "erreur": None,
            }
        )

        if i <= N_AFFICHAGE_MAX:
            print()
            print(f"[{i}/{len(fichiers_json)}] {fichier.name}")
            print(f"  datePublication brute : {date_brute}")
            print(f"  datePublication date  : {date_iso}")
            print(f"  heure                 : {heure}")
            print(f"  fuseau                : {fuseau}")
            print(f"  dateDepot             : {date_depot}")
            print(f"  numeroLong            : {numero_long}")
            print(f"  uid                   : {uid}")

    except Exception as erreur:
        lignes.append(
            {
                "fichier": fichier.name,
                "chemin": str(fichier),
                "datePublication_brute": None,
                "datePublication_date": None,
                "datePublication_heure": None,
                "datePublication_fuseau": None,
                "dateDepot": None,
                "uid": None,
                "numeroLong": None,
                "erreur": str(erreur),
            }
        )

        print(f"Erreur sur {fichier.name} : {erreur}")


#%%
# ---------------------------------------------------------------------
# RESULTAT EN POLARS
# ---------------------------------------------------------------------

df_dates = pl.DataFrame(lignes)

df_dates
# %%
