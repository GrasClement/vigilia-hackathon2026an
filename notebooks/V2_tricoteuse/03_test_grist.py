#%%
import requests
import polars as pl
import ast
from veille.filter_user import filtrer_amendements_mots_cles
from run.pipeline_amendements import traiter_amendements_jour
from veille.filter_user import filtrer_amendements_mots_cles


#%%
df_amendements_clean = traiter_amendements_jour("2026-07-01")

df_amendements_clean.head()

#%%
df_filtre = filtrer_amendements_mots_cles(
    df_amendements_clean,
    mots_expose=[
        "enfants",
    ],
    mots_dossier_ref_uid=[
        "DLR5L17N53980",
    ],
    mots_auteur_nom=[
        "Bonnivard",
        "Fruchon",
    ],
)



#%%
# Identifiants
DOC_ID = "3XJJmJ8TeyMcRWHEUNj4if"
API_KEY = "VOTRE_API_KEY"

BASE_URL = "https://docs.getgrist.com/api"

headers = {
    "Authorization": f"Bearer {API_KEY}"
}

#%%
url = f"{BASE_URL}/docs/{DOC_ID}/tables"

response = requests.get(url)

print(response.status_code)
print(response.json())
# %%
TABLE_ID = "Test_pipeline"

url = f"{BASE_URL}/docs/{DOC_ID}/tables/{TABLE_ID}/records"

response = requests.get(url)

print(response.status_code)

data = response.json()
records = data["records"]

print(records[:5])
# %%
df = pl.DataFrame([r["fields"] for r in records])

print(df)


# %%
def parse_mots(x):
    if x is None:
        return []

    x = str(x).strip()

    if x == "" or x.lower() in {"null", "none", "nan"}:
        return []

    return [mot.strip() for mot in x.split(",") if mot.strip()]


def get_keywords_from_grist(df_grist: pl.DataFrame) -> dict:
    # On garde seulement les lignes actives
    if "Active" in df_grist.columns:
        df_grist = df_grist.filter(pl.col("Active") == 1)

    if df_grist.height == 0:
        return {
            "Termes": [],
            "Noms": [],
            "Dossiers": [],
        }

    # Si tu n'as qu'une seule ligne active
    row = df_grist.row(0, named=True)

    return {
        "Termes": parse_mots(row.get("Termes")),
        "Noms": parse_mots(row.get("Noms")),
        "Dossiers": parse_mots(row.get("Dossiers")),
    }

# %%
params = get_keywords_from_grist(df)

termes = params.get("Termes", [])
noms = params.get("Noms", [])
dossiers = params.get("Dossiers", [])

print(termes)
print(noms)
print(dossiers)


# %%
df_filtre = filtrer_amendements_mots_cles(
    df= df_amendements_clean,
    mots_expose=termes,
    mots_auteur_nom=noms,
    mots_dossier_ref_uid=dossiers,
)


# %%
import polars as pl


def parse_mots(x):
    if x is None:
        return []

    x = str(x).strip()

    if x == "" or x.lower() in {"null", "none", "nan"}:
        return []

    return [mot.strip() for mot in x.split(",") if mot.strip()]


def get_veilles_from_grist(df_grist: pl.DataFrame) -> list[dict]:
    if "Active" in df_grist.columns:
        df_grist = df_grist.filter(pl.col("Active") == 1)

    veilles = []

    for i, row in enumerate(df_grist.iter_rows(named=True), start=1):
        veille = {
            "veille_id": i,
            "termes": parse_mots(row.get("Termes")),
            "noms": parse_mots(row.get("Noms")),
            "dossiers": parse_mots(row.get("Dossiers")),
            "source": row.get("Source"),
        }

        veilles.append(veille)

    return veilles

#%%
veilles = get_veilles_from_grist(df)

for veille in veilles:
    print(veille)



# %%
resultats_veilles = []

for veille in veilles:
    df_filtre = filtrer_amendements_mots_cles(
        df=df_amendements_clean,
        mots_expose=veille["termes"],
        mots_auteur_nom=veille["noms"],
        mots_dossier_ref_uid=veille["dossiers"],
    )

    df_filtre = df_filtre.with_columns(
        pl.lit(veille["veille_id"]).alias("veille_id"),
        pl.lit(", ".join(veille["termes"])).alias("veille_termes"),
        pl.lit(", ".join(veille["noms"])).alias("veille_noms"),
        pl.lit(", ".join(veille["dossiers"])).alias("veille_dossiers"),
    )

    resultats_veilles.append(df_filtre)
# %%
if resultats_veilles:
    df_resultats = pl.concat(resultats_veilles, how="diagonal")
else:
    df_resultats = pl.DataFrame()
# %%
