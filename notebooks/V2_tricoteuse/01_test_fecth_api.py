#%%
from veille.fetch_api import build_url, fetch_periode, fetch_jour
import requests

# %%
DOC_ID = "3XJJmJ8TeyMcRWHEUNj4if"
BASE_URL = "https://docs.getgrist.com/api"

url_doc = f"{BASE_URL}/docs/{DOC_ID}"

response = requests.get(url_doc)

print("Statut HTTP :", response.status_code)
print(response.json())



# %%
url_tables = f"{BASE_URL}/docs/{DOC_ID}/tables"

response = requests.get(url_tables)

print("Statut HTTP :", response.status_code)
print(response.json())


# %%
TABLE_ID = "Test_pipeline"  # à remplacer par le nom trouvé juste avant

url_records = f"{BASE_URL}/docs/{DOC_ID}/tables/{TABLE_ID}/records"

response = requests.get(
    url_records,
)

print("Statut HTTP :", response.status_code)

records = response.json()
print(records)


#%%
ammend = fetch_jour(
    resource="amendements",
    jour="2026-07-01"
)

#%%
import json
import polars as pl


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

    # Liste complète des colonnes, même si certaines sont absentes
    # dans certains amendements.
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

#%%
df_amendements = liste_api_vers_polars(ammend)

print(df_amendements.shape)
print(df_amendements.columns)

df_amendements.head()
# %%
from collections.abc import Sequence

#%%
import json
import polars as pl

#%%
def selectionner_colonnes_amendements(df: pl.DataFrame) -> pl.DataFrame:
    """
    Sélectionne les colonnes utiles des amendements et extrait les
    principales informations sur l'auteur et le dossier législatif.
    """

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
    ]

    colonnes_presentes = [c for c in colonnes_base if c in df.columns]

    df = df.select(colonnes_presentes)

    def extraire_acteur(acteur_ref: str | None) -> dict:
        if not acteur_ref:
            return {
                "auteur_uid": None,
                "auteur_nom": None,
                "auteur_prenom": None,
                "auteur_civ": None,
                "auteur_chambre": None,
                "groupe_politique": None,
                "groupe_politique_abrege": None,
                "couleur_politique": None,
            }

        try:
            acteur = json.loads(acteur_ref)
        except Exception:
            return {
                "auteur_uid": None,
                "auteur_nom": None,
                "auteur_prenom": None,
                "auteur_civ": None,
                "auteur_chambre": None,
                "groupe_politique": None,
                "groupe_politique_abrege": None,
                "couleur_politique": None,
            }

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

    def extraire_dossier(dossier_ref: str | None) -> dict:
        if not dossier_ref:
            return {
                "dossier_uid": None,
                "dossier_ref_uid": None,
                "titre_dossier": None,
                "titre_dossier_court": None,
            }

        try:
            dossier = json.loads(dossier_ref)
        except Exception:
            return {
                "dossier_uid": None,
                "dossier_ref_uid": None,
                "titre_dossier": None,
                "titre_dossier_court": None,
            }

        return {
            "dossier_uid": dossier.get("uid"),
            "dossier_ref_uid": dossier.get("dossierRefUid"),
            "titre_dossier": dossier.get("titrePrincipal"),
            "titre_dossier_court": dossier.get("titrePrincipalCourt"),
        }

    df_acteurs = pl.from_dicts(
        [extraire_acteur(x) for x in df["acteurRef"].to_list()]
    )

    df_dossiers = pl.from_dicts(
        [extraire_dossier(x) for x in df["documentRef"].to_list()]
    )

    return (
        pl.concat(
            [
                df.drop(["acteurRef", "documentRef"]),
                df_acteurs,
                df_dossiers,
            ],
            how="horizontal",
        )
    )
#%%
df_amendements_clean = selectionner_colonnes_amendements(df_amendements)

df_amendements_clean.head()



#%%
