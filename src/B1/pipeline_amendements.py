from __future__ import annotations

import json

import polars as pl

from veille.fetch_api import fetch_jour


def traiter_amendements_jour(jour: str) -> pl.DataFrame:
    """
    Pipeline complet pour une journée :
    1. fetch_jour sur les amendements ;
    2. conversion robuste en Polars ;
    3. sélection des colonnes utiles ;
    4. extraction des infos auteur ;
    5. extraction des infos dossier depuis documentRef.
    """

    items = fetch_jour(
        resource="amendements",
        jour=jour,
    )

    df = liste_api_vers_polars(items)

    return selectionner_colonnes_amendements(df)


def liste_api_vers_polars(items: list[dict]) -> pl.DataFrame:
    """
    Transforme une liste de dictionnaires API en DataFrame Polars.

    Toutes les valeurs sont converties en texte pour éviter les erreurs
    de types incohérents provenant de l'API Tricoteuses.
    """
    if not items:
        return pl.DataFrame()

    def vers_texte(valeur) -> str | None:
        if valeur is None:
            return None

        if isinstance(valeur, (dict, list, tuple, set)):
            return json.dumps(
                valeur,
                ensure_ascii=False,
                default=str,
            )

        return str(valeur)

    colonnes = list(
        dict.fromkeys(
            colonne
            for item in items
            for colonne in item
        )
    )

    lignes = [
        {
            colonne: vers_texte(item.get(colonne))
            for colonne in colonnes
        }
        for item in items
    ]

    schema = {
        colonne: pl.String
        for colonne in colonnes
    }

    return pl.from_dicts(
        lignes,
        schema=schema,
        strict=False,
    )


def selectionner_colonnes_amendements(df: pl.DataFrame) -> pl.DataFrame:
    """
    Sélectionne les colonnes utiles des amendements et extrait :
    - les informations essentielles de l'auteur depuis acteurRef ;
    - les informations du dossier depuis documentRef.
    """

    if df.is_empty():
        return df

    colonnes_base = [
        "uid",
        "typeAuteur",
        "dispositif",
        "exposeSommaire",
        "sortAmendement",
        "etatLibelle",
        "nombreCoSignataires",
        "acteurRef",
        "documentRef",
        "dateDepot",
        
    ]

    colonnes_presentes = [
        col for col in colonnes_base
        if col in df.columns
    ]

    df = df.select(colonnes_presentes)

    def extraire_acteur(acteur_ref: str | None) -> dict:
        vide = {
            "auteur_uid": None,
            "auteur_nom": None,
            "auteur_prenom": None,
            "auteur_civ": None,
            "auteur_chambre": None,
            "groupe_politique": None,
            "groupe_politique_abrege": None,
            "couleur_politique": None,
        }

        if not acteur_ref:
            return vide

        try:
            acteur = json.loads(acteur_ref)
        except Exception:
            return vide

        groupe = acteur.get("groupeParlementaire") or {}

        return {
            "auteur_uid": acteur.get("uid"),
            "auteur_nom": acteur.get("nom"),
            "auteur_prenom": acteur.get("prenom"),
            "auteur_civ": acteur.get("civ"),
            "auteur_chambre": acteur.get("chambre"),
            "groupe_politique": groupe.get("libelle"),
            "groupe_politique_abrege": groupe.get("libelleAbrege"),
            "couleur_politique": groupe.get("couleurAssociee"),
        }

    def extraire_dossier(document_ref: str | None) -> dict:
        vide = {
            "document_uid": None,
            "dossier_ref_uid": None,
            "titre_dossier": None,
            "titre_dossier_court": None,
        }

        if not document_ref:
            return vide

        try:
            document = json.loads(document_ref)
        except Exception:
            return vide

        return {
            "document_uid": document.get("uid"),
            "dossier_ref_uid": document.get("dossierRefUid"),
            "titre_dossier": document.get("titrePrincipal"),
            "titre_dossier_court": document.get("titrePrincipalCourt"),
        }

    df_acteurs = pl.from_dicts(
        [extraire_acteur(x) for x in df["acteurRef"].to_list()]
    )

    df_documents = pl.from_dicts(
        [extraire_dossier(x) for x in df["documentRef"].to_list()]
    )

    return pl.concat(
        [
            df.drop(["acteurRef", "documentRef"]),
            df_acteurs,
            df_documents,
        ],
        how="horizontal",
    )