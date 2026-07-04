from __future__ import annotations

"""
Pipeline complète de veille parlementaire.

Cette module :
1. lit les requêtes de veille dans une table Grist ;
2. récupère et nettoie les amendements sur une période ;
3. applique chaque veille ;
4. concatène les résultats par veille ;
5. crée / met à jour les tables de sortie dans Grist.

Exemple :
    bilan = executer_pipeline_veilles(
        date_reference="2026-07-04",
        gap=3,
        doc_id=DOC_ID,
        api_key=API_KEY,
        table_requetes="Test_pipeline",
        prefixe_sortie="Sortie_test",
    )
"""

from collections import defaultdict
from datetime import date, datetime, timedelta
import json
import math
from typing import Any

import polars as pl
import requests

from B1.pipeline_amendements import traiter_amendements_jour
from veille.filter_user import filtrer_amendements_mots_cles


BASE_URL_GRIST = "https://grist.numerique.gouv.fr/o/docs/api"
DEFAULT_TIMEOUT = 30


# ============================================================================
# Dates
# ============================================================================

def normaliser_date_reference(
    date_reference: str | date | datetime | None = None,
) -> date:
    """Convertit une date texte, date ou datetime en objet date.

    Si date_reference vaut None, utilise la date locale de la machine.
    Le format texte attendu est YYYY-MM-DD.
    """
    if date_reference is None:
        return date.today()

    if isinstance(date_reference, datetime):
        return date_reference.date()

    if isinstance(date_reference, date):
        return date_reference

    if isinstance(date_reference, str):
        try:
            return datetime.strptime(date_reference, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValueError(
                "date_reference doit être au format 'YYYY-MM-DD', "
                f"reçu : {date_reference!r}"
            ) from exc

    raise TypeError(
        "date_reference doit être une str, date, datetime ou None."
    )


def construire_jours_a_traiter(
    date_reference: str | date | datetime | None = None,
    gap: int = 0,
) -> list[str]:
    """Construit les jours à traiter, bornes incluses.

    gap=0  -> [date_reference]
    gap=3  -> [date_reference - 3 jours, ..., date_reference]

    Le gap représente donc le nombre de jours *avant* la date de référence
    que l'on veut aussi inclure.
    """
    if not isinstance(gap, int) or gap < 0:
        raise ValueError("gap doit être un entier positif ou nul.")

    fin = normaliser_date_reference(date_reference)
    debut = fin - timedelta(days=gap)

    return [
        (debut + timedelta(days=i)).isoformat()
        for i in range(gap + 1)
    ]


# ============================================================================
# Lecture et interprétation de la table de requêtes Grist
# ============================================================================

def _headers_grist(api_key: str) -> dict[str, str]:
    if not api_key or not api_key.strip():
        raise ValueError("api_key ne peut pas être vide.")

    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def parse_mots(x: Any) -> list[str]:
    """Transforme une cellule Grist 'mot1, mot2' en liste de termes."""
    if x is None:
        return []

    x = str(x).strip()

    if x == "" or x.lower() in {"null", "none", "nan"}:
        return []

    return [mot.strip() for mot in x.split(",") if mot.strip()]


def lire_table_grist(
    doc_id: str,
    table_id: str,
    api_key: str,
    base_url: str = BASE_URL_GRIST,
    timeout: int = DEFAULT_TIMEOUT,
) -> pl.DataFrame:
    """Lit une table Grist et renvoie les champs sous forme de DataFrame Polars."""
    url = f"{base_url}/docs/{doc_id}/tables/{table_id}/records"

    response = requests.get(
        url,
        headers=_headers_grist(api_key),
        timeout=timeout,
    )
    response.raise_for_status()

    records = response.json().get("records", [])

    if not records:
        return pl.DataFrame()

    return pl.DataFrame([record["fields"] for record in records])


def _est_active(valeur: Any) -> bool:
    """Interprète les valeurs usuelles de la colonne Active."""
    if isinstance(valeur, bool):
        return valeur

    if isinstance(valeur, (int, float)) and not isinstance(valeur, bool):
        return valeur == 1

    if valeur is None:
        return False

    return str(valeur).strip().lower() in {
        "1", "true", "vrai", "yes", "oui", "x",
    }

def extraire_veilles_actives(df_grist: pl.DataFrame) -> list[dict[str, Any]]:
    """
    Extrait les veilles actives et ignore les lignes actives sans aucun filtre.

    Une veille doit contenir au moins un élément dans :
    - Termes
    - Noms
    - Dossiers
    """
    if df_grist.is_empty():
        return []

    if "Active" in df_grist.columns:
        actifs = [
            _est_active(x)
            for x in df_grist["Active"].to_list()
        ]
        df_grist = df_grist.filter(pl.Series(actifs))

    veilles = []

    for numero_ligne, row in enumerate(
        df_grist.iter_rows(named=True),
        start=1,
    ):
        termes = parse_mots(row.get("Termes"))
        noms = parse_mots(row.get("Noms"))
        dossiers = parse_mots(row.get("Dossiers"))

        # Évite une veille active mais vide, qui ferait planter le filtre.
        if not any([termes, noms, dossiers]):
            print(
                f"Veille active ignorée (ligne {numero_ligne}) : "
                "aucun terme, nom ou dossier renseigné."
            )
            continue

        veilles.append(
            {
                "nom": f"veille_{len(veilles) + 1}",
                "veille_id": len(veilles) + 1,
                "termes": termes,
                "noms": noms,
                "dossiers": dossiers,
                "source": row.get("Source"),
            }
        )

    return veilles
# ============================================================================
# Application des veilles
# ============================================================================

def _ajouter_metadonnees_veille(
    df: pl.DataFrame,
    jour: str,
    veille: dict[str, Any],
) -> pl.DataFrame:
    """Ajoute les informations de contexte nécessaires au suivi Grist."""
    return df.with_columns(
        pl.lit(jour).alias("jour_veille"),
        pl.lit(veille["veille_id"]).alias("veille_id"),
        pl.lit(veille["nom"]).alias("veille_nom"),
        pl.lit(", ".join(veille["termes"])).alias("veille_termes"),
        pl.lit(", ".join(veille["noms"])).alias("veille_noms"),
        pl.lit(", ".join(veille["dossiers"])).alias("veille_dossiers"),
        pl.lit(veille["source"]).alias("veille_source"),
    )


def appliquer_veilles_sur_periode(
    jours: list[str],
    veilles: list[dict[str, Any]],
    continuer_si_erreur: bool = False,
    verbose: bool = True,
) -> tuple[dict[str, pl.DataFrame], dict[str, str]]:
    """Récupère, nettoie puis filtre les amendements pour tous les jours.

    Renvoie :
    - un dictionnaire {nom_veille: DataFrame} ;
    - un dictionnaire {jour: message_erreur} si continuer_si_erreur=True.

    Une requête API échouée interrompt par défaut le pipeline : cela évite
    d'exporter silencieusement une période incomplète.
    """
    morceaux: dict[str, list[pl.DataFrame]] = defaultdict(list)
    erreurs: dict[str, str] = {}

    for jour in jours:
        if verbose:
            print(f"[{jour}] récupération et nettoyage des amendements...")

        try:
            df_amendements = traiter_amendements_jour(jour)
        except Exception as exc:
            if not continuer_si_erreur:
                raise RuntimeError(
                    f"Échec pendant le traitement des amendements du {jour}."
                ) from exc

            erreurs[jour] = f"{type(exc).__name__}: {exc}"
            if verbose:
                print(f"[{jour}] ERREUR ignorée : {erreurs[jour]}")
            continue

        if df_amendements.is_empty():
            if verbose:
                print(f"[{jour}] aucun amendement récupéré.")
            continue

        if verbose:
            print(
                f"[{jour}] {df_amendements.height} amendement(s) "
                f"avant filtrage."
            )

        for veille in veilles:
            df_filtre = filtrer_amendements_mots_cles(
                df=df_amendements,
                mots_expose=veille["termes"],
                mots_auteur_nom=veille["noms"],
                mots_dossier_ref_uid=veille["dossiers"],
            )

            if not df_filtre.is_empty():
                morceaux[veille["nom"]].append(
                    _ajouter_metadonnees_veille(
                        df=df_filtre,
                        jour=jour,
                        veille=veille,
                    )
                )

    resultats: dict[str, pl.DataFrame] = {}

    for veille in veilles:
        nom = veille["nom"]
        morceaux_veille = morceaux.get(nom, [])

        if not morceaux_veille:
            resultats[nom] = pl.DataFrame()
            continue

        df_veille = pl.concat(morceaux_veille, how="diagonal_relaxed")

        # Une même ressource peut théoriquement être renvoyée plus d'une fois.
        # uid est l'identifiant naturel de l'amendement.
        if "uid" in df_veille.columns:
            df_veille = df_veille.unique(
                subset=["uid"],
                maintain_order=True,
            )

        resultats[nom] = df_veille

        if verbose:
            print(
                f"[{nom}] {df_veille.height} amendement(s) "
                "retenu(s) sur la période."
            )

    return resultats, erreurs


# ============================================================================
# Écriture robuste dans Grist
# ============================================================================

def valeur_grist(x: Any) -> str | None:
    """Convertit une valeur Python en valeur compatible avec une colonne Text."""
    if x is None:
        return None

    if isinstance(x, float) and math.isnan(x):
        return None

    if isinstance(x, (list, tuple, set, dict)):
        return json.dumps(
            x,
            ensure_ascii=False,
            default=str,
        )

    return str(x)


def table_existe_grist(
    doc_id: str,
    table_id: str,
    api_key: str,
    base_url: str = BASE_URL_GRIST,
    timeout: int = DEFAULT_TIMEOUT,
) -> bool:
    """Indique si l'identifiant technique d'une table existe dans Grist."""
    response = requests.get(
        f"{base_url}/docs/{doc_id}/tables",
        headers=_headers_grist(api_key),
        timeout=timeout,
    )
    response.raise_for_status()

    return table_id in {
        table["id"]
        for table in response.json().get("tables", [])
    }


def _definition_colonnes_textuelles(
    colonnes: list[str],
) -> list[dict[str, Any]]:
    """Construit le schéma de colonnes Text transmis à Grist."""
    return [
        {
            "id": colonne,
            "fields": {
                "label": colonne,
                "type": "Text",
            },
        }
        for colonne in colonnes
    ]


def creer_table_grist_depuis_df(
    df: pl.DataFrame,
    doc_id: str,
    table_id: str,
    api_key: str,
    base_url: str = BASE_URL_GRIST,
    timeout: int = DEFAULT_TIMEOUT,
) -> bool:
    """Crée une table Grist à partir du schéma du DataFrame si nécessaire.

    Renvoie True lorsque la table vient d'être créée, False sinon.
    """
    if table_existe_grist(
        doc_id=doc_id,
        table_id=table_id,
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
    ):
        return False

    if not df.columns:
        raise ValueError(
            "Impossible de créer une table Grist à partir d'un DataFrame "
            "sans colonnes."
        )

    payload = {
        "tables": [
            {
                "id": table_id,
                "columns": _definition_colonnes_textuelles(df.columns),
            }
        ]
    }

    response = requests.post(
        f"{base_url}/docs/{doc_id}/tables",
        headers=_headers_grist(api_key),
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()

    return True


def recuperer_mapping_colonnes_grist(
    doc_id: str,
    table_id: str,
    api_key: str,
    base_url: str = BASE_URL_GRIST,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, str]:
    """Renvoie {label_affiché: id_technique} pour une table Grist.

    Grist peut modifier l'id technique d'une colonne. Exemple :
    '_filtres_trouves' devient l'id 'filtres_trouves'. C'est donc ce mapping
    qu'il faut utiliser pour écrire les records.
    """
    response = requests.get(
        f"{base_url}/docs/{doc_id}/tables/{table_id}/columns",
        headers=_headers_grist(api_key),
        timeout=timeout,
    )
    response.raise_for_status()

    return {
        colonne["fields"]["label"]: colonne["id"]
        for colonne in response.json().get("columns", [])
    }


def ajouter_colonnes_manquantes_grist(
    colonnes: list[str],
    doc_id: str,
    table_id: str,
    api_key: str,
    base_url: str = BASE_URL_GRIST,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, str]:
    """Ajoute les colonnes absentes et retourne le mapping final label -> id."""
    mapping = recuperer_mapping_colonnes_grist(
        doc_id=doc_id,
        table_id=table_id,
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
    )

    colonnes_manquantes = [
        colonne
        for colonne in colonnes
        if colonne not in mapping
    ]

    if not colonnes_manquantes:
        return mapping

    payload = {
        "columns": _definition_colonnes_textuelles(colonnes_manquantes)
    }

    response = requests.post(
        f"{base_url}/docs/{doc_id}/tables/{table_id}/columns",
        headers=_headers_grist(api_key),
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()

    return recuperer_mapping_colonnes_grist(
        doc_id=doc_id,
        table_id=table_id,
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
    )


def vider_table_grist(
    doc_id: str,
    table_id: str,
    api_key: str,
    base_url: str = BASE_URL_GRIST,
    batch_size: int = 100,
    timeout: int = DEFAULT_TIMEOUT,
) -> int:
    """Supprime tous les records d'une table, sans toucher à son schéma."""
    response = requests.get(
        f"{base_url}/docs/{doc_id}/tables/{table_id}/records",
        headers=_headers_grist(api_key),
        timeout=timeout,
    )
    response.raise_for_status()

    ids = [
        record["id"]
        for record in response.json().get("records", [])
    ]

    for i in range(0, len(ids), batch_size):
        response = requests.post(
            f"{base_url}/docs/{doc_id}/tables/{table_id}/records/delete",
            headers=_headers_grist(api_key),
            json=ids[i:i + batch_size],
            timeout=timeout,
        )
        response.raise_for_status()

    return len(ids)


def importer_df_dans_grist(
    df: pl.DataFrame,
    doc_id: str,
    table_id: str,
    api_key: str,
    base_url: str = BASE_URL_GRIST,
    batch_size: int = 100,
    mode_export: str = "append",
    timeout: int = DEFAULT_TIMEOUT,
) -> int:
    """Crée/complète une table Grist puis écrit un DataFrame Polars.

    mode_export :
    - "append"  : ajoute les lignes à la fin de la table ;
    - "replace" : supprime les lignes existantes puis écrit le DataFrame.

    Les tables et colonnes existantes sont conservées. Les nouvelles colonnes
    du DataFrame sont ajoutées automatiquement.
    """
    if mode_export not in {"append", "replace"}:
        raise ValueError("mode_export doit être 'append' ou 'replace'.")

    if df.is_empty():
        if mode_export == "replace" and table_existe_grist(
            doc_id=doc_id,
            table_id=table_id,
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        ):
            vider_table_grist(
                doc_id=doc_id,
                table_id=table_id,
                api_key=api_key,
                base_url=base_url,
                batch_size=batch_size,
                timeout=timeout,
            )
        return 0

    creer_table_grist_depuis_df(
        df=df,
        doc_id=doc_id,
        table_id=table_id,
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
    )

    mapping = ajouter_colonnes_manquantes_grist(
        colonnes=df.columns,
        doc_id=doc_id,
        table_id=table_id,
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
    )

    if mode_export == "replace":
        vider_table_grist(
            doc_id=doc_id,
            table_id=table_id,
            api_key=api_key,
            base_url=base_url,
            batch_size=batch_size,
            timeout=timeout,
        )

    records = [
        {
            "fields": {
                mapping[colonne]: valeur_grist(valeur)
                for colonne, valeur in ligne.items()
            }
        }
        for ligne in df.iter_rows(named=True)
    ]

    url = f"{base_url}/docs/{doc_id}/tables/{table_id}/records?noparse=true"

    total = 0

    for i in range(0, len(records), batch_size):
        response = requests.post(
            url,
            headers=_headers_grist(api_key),
            json={"records": records[i:i + batch_size]},
            timeout=timeout,
        )
        response.raise_for_status()
        total += len(records[i:i + batch_size])

    return total


# ============================================================================
# Pipeline publique : un seul appel
# ============================================================================

def executer_pipeline_veilles(
    date_reference: str | date | datetime | None,
    gap: int,
    doc_id: str,
    api_key: str,
    table_requetes: str,
    prefixe_sortie: str = "Sortie",
    base_url: str = BASE_URL_GRIST,
    mode_export: str = "replace",
    ignorer_tables_vides: bool = True,
    batch_size: int = 100,
    continuer_si_erreur: bool = False,
    verbose: bool = True,
) -> dict[str, Any]:
    """Exécute la veille complète, de l'API Tricoteuses à Grist.

    Paramètres principaux
    ---------------------
    date_reference :
        Date de fin au format "YYYY-MM-DD". None utilise la date locale.
    gap :
        Nombre de jours avant date_reference à inclure.
        Exemple : date_reference="2026-07-04", gap=3 traite les 1er, 2, 3
        et 4 juillet 2026.
    doc_id / api_key :
        Identifiants d'accès au document Grist.
    table_requetes :
        Identifiant technique de la table Grist contenant les requêtes :
        colonnes usuelles Active, Termes, Noms, Dossiers, Source.
    prefixe_sortie :
        Chaque veille crée/alimente une table :
        {prefixe_sortie}_veille_1, {prefixe_sortie}_veille_2, etc.
    mode_export :
        "replace" remplace entièrement le contenu des tables de sortie ;
        "append" ajoute les nouvelles lignes sans supprimer l'existant.
    ignorer_tables_vides :
        Si True, ne crée/écrit pas une table lorsqu'une veille ne renvoie rien.

    Retour
    ------
    Dictionnaire comprenant les jours traités, les comptes par table, les
    erreurs éventuellement ignorées et les DataFrames filtrés.
    """
    jours = construire_jours_a_traiter(
        date_reference=date_reference,
        gap=gap,
    )

    if verbose:
        print(
            "Lecture des requêtes dans "
            f"Grist : table '{table_requetes}'..."
        )

    df_requetes = lire_table_grist(
        doc_id=doc_id,
        table_id=table_requetes,
        api_key=api_key,
        base_url=base_url,
    )

    veilles = extraire_veilles_actives(df_requetes)

    if not veilles:
        if verbose:
            print("Aucune veille active : aucun appel API ni export.")

        return {
            "jours": jours,
            "nombre_veilles_actives": 0,
            "tables": {},
            "erreurs_jours": {},
            "resultats": {},
        }

    if verbose:
        print(f"{len(veilles)} veille(s) active(s) trouvée(s).")

    resultats, erreurs_jours = appliquer_veilles_sur_periode(
        jours=jours,
        veilles=veilles,
        continuer_si_erreur=continuer_si_erreur,
        verbose=verbose,
    )

    tables: dict[str, int] = {}

    for veille in veilles:
        nom_veille = veille["nom"]
        table_sortie = f"{prefixe_sortie}_{nom_veille}"
        df_sortie = resultats[nom_veille]

        if df_sortie.is_empty() and ignorer_tables_vides:
            tables[table_sortie] = 0
            if verbose:
                print(
                    f"[{table_sortie}] aucune ligne : "
                    "export ignoré."
                )
            continue

        nb_lignes = importer_df_dans_grist(
            df=df_sortie,
            doc_id=doc_id,
            table_id=table_sortie,
            api_key=api_key,
            base_url=base_url,
            batch_size=batch_size,
            mode_export=mode_export,
        )

        tables[table_sortie] = nb_lignes

        if verbose:
            print(
                f"[{table_sortie}] {nb_lignes} ligne(s) "
                f"exportée(s), mode={mode_export}."
            )

    return {
        "jours": jours,
        "nombre_veilles_actives": len(veilles),
        "tables": tables,
        "erreurs_jours": erreurs_jours,
        "resultats": resultats,
    }
