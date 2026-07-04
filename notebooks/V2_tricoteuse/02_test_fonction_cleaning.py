
#%%
from run.pipeline_amendements import traiter_amendements_jour

#%%

df_amendements_clean = traiter_amendements_jour("2026-07-01")

df_amendements_clean.head()
# %%
from veille.filter_user import filtrer_amendements_mots_cles

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

# %%
