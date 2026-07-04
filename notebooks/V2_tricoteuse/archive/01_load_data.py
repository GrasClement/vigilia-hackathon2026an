#%%
from __future__ import annotations

import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from urllib.parse import quote

import requests

#%%
# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

BASE_URL = "https://git.en-root.org/api/v4"

PROJECT = (
    "tricoteuses/data/assemblee-nettoye/"
    "Amendements_XVII_nettoye"
)

# "master" = version actuelle du dépôt.
# Tu peux aussi mettre un hash précis de commit pour figer la version.
REF = "master"

PROJECT_ID = quote(PROJECT, safe="")

# Archive téléchargée temporairement / conservée localement
ARCHIVE_DIR = Path("data") / "_archives"

# Tous les JSON seront extraits ici
OUTPUT_DIR = Path("data") / "amendements"

# Fichier qui garde une trace de la version téléchargée
MANIFEST_PATH = OUTPUT_DIR / "_tricoteuses_manifest.json"


# ---------------------------------------------------------------------
# Téléchargement de l'archive complète du dépôt
# ---------------------------------------------------------------------

def telecharger_archive() -> Path:
    """
    Télécharge le dépôt Tricoteuses entier sous forme de ZIP.

    Ne clone pas Git et ne fait pas une requête HTTP par fichier.
    """
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    archive_path = ARCHIVE_DIR / f"amendements_xvii_{REF}.zip"
    temp_path = archive_path.with_suffix(".tmp")

    url = (
        f"{BASE_URL}/projects/{PROJECT_ID}/"
        "repository/archive.zip"
    )

    print("Téléchargement de l'archive GitLab...")

    with requests.get(
        url,
        params={
            "sha": REF,
            "include_lfs_blobs": "false",
        },
        stream=True,
        timeout=(30, 600),
    ) as response:
        response.raise_for_status()

        taille_totale = int(response.headers.get("Content-Length", 0))
        taille_telechargee = 0

        with temp_path.open("wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue

                f.write(chunk)
                taille_telechargee += len(chunk)

                if taille_totale:
                    pourcentage = 100 * taille_telechargee / taille_totale
                    print(
                        f"\rTéléchargé : {pourcentage:5.1f} %",
                        end="",
                        flush=True,
                    )

    print()

    temp_path.replace(archive_path)

    print(f"Archive enregistrée : {archive_path}")
    return archive_path


# ---------------------------------------------------------------------
# Extraction des JSON seulement
# ---------------------------------------------------------------------

def extraire_json(archive_path: Path) -> list[Path]:
    """
    Extrait uniquement les JSON de l'archive dans data/amendements/.

    L'arborescence Tricoteuses est conservée :
    PION.../AMANR....json
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    fichiers_extraits = []

    with zipfile.ZipFile(archive_path) as archive:
        infos_json = [
            info
            for info in archive.infolist()
            if not info.is_dir() and info.filename.endswith(".json")
        ]

        if not infos_json:
            raise RuntimeError("Aucun fichier JSON trouvé dans l'archive.")

        # GitLab ajoute généralement un dossier racine dans l'archive :
        # Amendements_XVII_nettoye-<commit>/...
        racines = {
            PurePosixPath(info.filename).parts[0]
            for info in infos_json
            if PurePosixPath(info.filename).parts
        }

        dossier_racine = next(iter(racines)) if len(racines) == 1 else None

        print(f"{len(infos_json)} JSON trouvés dans l'archive.")

        for i, info in enumerate(infos_json, start=1):
            chemin_zip = PurePosixPath(info.filename)

            # Sécurité : évite les chemins du type ../../...
            if ".." in chemin_zip.parts or chemin_zip.is_absolute():
                continue

            # On enlève le dossier racine ajouté par GitLab.
            if dossier_racine and chemin_zip.parts[0] == dossier_racine:
                chemin_relatif = PurePosixPath(*chemin_zip.parts[1:])
            else:
                chemin_relatif = chemin_zip

            destination = OUTPUT_DIR.joinpath(*chemin_relatif.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)

            with archive.open(info) as source, destination.open("wb") as cible:
                shutil.copyfileobj(source, cible)

            fichiers_extraits.append(destination)

            if i % 1_000 == 0 or i == len(infos_json):
                print(
                    f"Extraction : {i:,}/{len(infos_json):,}",
                    end="\r",
                    flush=True,
                )

    print()
    return fichiers_extraits


# ---------------------------------------------------------------------
# Manifest : mémorise ce que tu as téléchargé
# ---------------------------------------------------------------------

def enregistrer_manifest(
    archive_path: Path,
    fichiers_extraits: list[Path],
) -> None:
    manifest = {
        "source": PROJECT,
        "ref": REF,
        "archive": str(archive_path),
        "date_telechargement": datetime.now().isoformat(),
        "nombre_json": len(fichiers_extraits),
    }

    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------
# Lancement
# ---------------------------------------------------------------------

def main() -> None:
    archive_path = telecharger_archive()
    fichiers_extraits = extraire_json(archive_path)

    enregistrer_manifest(
        archive_path=archive_path,
        fichiers_extraits=fichiers_extraits,
    )

    print()
    print(f"Terminé : {len(fichiers_extraits):,} JSON extraits.")
    print(f"Dossier des amendements : {OUTPUT_DIR.resolve()}")


#%%
if __name__ == "__main__":
    main()
# %%
