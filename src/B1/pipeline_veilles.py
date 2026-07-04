from __future__ import annotations

import requests
import polars as pl

from B1.pipeline_amendements import traiter_amendements_jour
from veille.filter_user import filtrer_amendements_mots_cles


def parse_mots(x) -> list[str]:
    if x is None:
        return []

    x = str(x).strip()

    if x == "" or x.lower() in {"null", "none", "nan"}:
        return []

    return [mot.strip() for mot in x.split(",") if mot.strip()]


def lire_table_grist(
    doc_id: str,
    table_id: str,
    api_key: str | None = None,
    base_url: str = "https://docs.getgrist.com/api",
) -> pl.DataFrame:
    url = f"{base_url}/docs/{doc_id}/tables/{table_id}/records"

    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    records = response.json()["records"]

    if not records:
        return pl.DataFrame()

    return pl.DataFrame([record["fields"] for record in records])


def extraire_veilles_actives(df_grist: pl.DataFrame) -> list[dict]:
    if df_grist.is_empty():
        return []

    if "Active" in df_grist.columns:
        df_grist = df_grist.filter(pl.col("Active") == 1)

    veilles = []

    for i, row in enumerate(df_grist.iter_rows(named=True), start=1):
        veilles.append(
            {
                "nom": f"veille_{i}",
                "veille_id": i,
                "termes": parse_mots(row.get("Termes")),
                "noms": parse_mots(row.get("Noms")),
                "dossiers": parse_mots(row.get("Dossiers")),
                "source": row.get("Source"),
            }
        )

    return veilles


def pipeline_veilles_amendements_jour(
    jour: str,
    doc_id: str,
    table_id: str,
    api_key: str | None = None,
    base_url: str = "https://docs.getgrist.com/api",
) -> tuple[pl.DataFrame, ...]:
    """
    Pipeline complet.

    Elle :
    1. récupère les amendements du jour ;
    2. nettoie les amendements ;
    3. lit les veilles actives dans Grist ;
    4. applique une veille par ligne active ;
    5. renvoie directement plusieurs DataFrames.

    Exemple :
        veille_1, veille_2 = pipeline_veilles_amendements_jour(...)
    """

    df_amendements_clean = traiter_amendements_jour(jour)

    df_grist = lire_table_grist(
        doc_id=doc_id,
        table_id=table_id,
        api_key=api_key,
        base_url=base_url,
    )

    veilles = extraire_veilles_actives(df_grist)

    resultats = []

    for veille in veilles:
        df_filtre = filtrer_amendements_mots_cles(
            df=df_amendements_clean,
            mots_expose=veille["termes"],
            mots_auteur_nom=veille["noms"],
            mots_dossier_ref_uid=veille["dossiers"],
        )

        df_filtre = df_filtre.with_columns(
            pl.lit(jour).alias("jour_veille"),
            pl.lit(veille["veille_id"]).alias("veille_id"),
            pl.lit(veille["nom"]).alias("veille_nom"),
            pl.lit(", ".join(veille["termes"])).alias("veille_termes"),
            pl.lit(", ".join(veille["noms"])).alias("veille_noms"),
            pl.lit(", ".join(veille["dossiers"])).alias("veille_dossiers"),
            pl.lit(veille["source"]).alias("veille_source"),
        )

        resultats.append(df_filtre)

    return tuple(resultats)