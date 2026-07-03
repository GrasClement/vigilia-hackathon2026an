#%%
from veille.fetch_api import build_url, fetch_periode

# %%
amendements = fetch_periode(
    resource="amendements",
    date_debut="2026-07-01",
    date_fin="2026-07-02",
    search="agriculture",
    per_page=100,
)

print(f"{len(amendements)} amendements trouvés")


# %%
