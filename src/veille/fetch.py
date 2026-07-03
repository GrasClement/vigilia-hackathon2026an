"""Acquisition des amendements (bloc B1).

Option A : dépôt Git Tricoteuses (préférée, URL fixée au spike J0).
Option B : dump quotidien officiel de la législature (fallback garanti).
Les deux renvoient la même chose : une liste de JSON bruts d'amendements.
"""

import io
import json
import zipfile
from pathlib import Path

import requests

from veille import config


def fetch_dump(
    url: str = config.AN_DUMP_URL, cache_dir: str = config.DATA_DIR
) -> list[dict]:
    """Download and parse the daily legislature-wide amendments archive.

    The zip is cached on disk and not re-downloaded within the same day.

    Parameters
    ----------
    url : str, default=config.AN_DUMP_URL
        Archive URL on data.assemblee-nationale.fr.
    cache_dir : str, default=config.DATA_DIR
        Local cache directory (gitignored).

    Returns
    -------
    list of dict
        One parsed JSON per amendment of the legislature.

    Raises
    ------
    requests.HTTPError
        If the download fails.
    """
    cache = Path(cache_dir) / "amendements.json.zip"
    if not cache.exists():
        response = requests.get(url, timeout=300)
        response.raise_for_status()
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(response.content)

    archive = zipfile.ZipFile(io.BytesIO(cache.read_bytes()))
    return [
        json.loads(archive.read(name))
        for name in archive.namelist()
        if name.endswith(".json")
    ]


def fetch_tricoteuses(repo_dir: str = f"{config.DATA_DIR}/tricoteuses") -> list[dict]:
    """Pull the Tricoteuses repository and return new amendment JSONs.

    Dépôt confirmé : ``assemblee-brut/Amendements_XVII`` sur
    git.en-root.org (schéma AN brut, un JSON par amendement). ``git clone
    --depth 1`` au premier appel puis ``git pull``, le "quoi de neuf"
    étant donné par ``git diff --name-only ORIG_HEAD HEAD``.

    Parameters
    ----------
    repo_dir : str
        Local clone directory (gitignored).

    Returns
    -------
    list of dict
        One parsed JSON per new or updated amendment.
    """
    msg = "Option A à implémenter au spike J0 ; utiliser fetch_dump() en attendant."
    raise NotImplementedError(msg)
