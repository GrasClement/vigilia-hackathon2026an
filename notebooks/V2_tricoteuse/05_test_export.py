#%%
from B1.pipeline_veilles_v2 import (
    pipeline_veilles_amendements_jour,
    exporter_veilles_vers_grist,
)

DOC_ID = "3XJJmJ8TeyMcRWHEUNj4if"
TABLE_ID = "Test_pipeline"
API_KEY = "15ec820ee1f8d920cd7b82a4218f94969d8901ae"


#%%
resultats = pipeline_veilles_amendements_jour(
    jour="2026-07-01",
    doc_id=DOC_ID,
    table_id=TABLE_ID,
    api_key=API_KEY,
)


#%%
#%%
print(f"{len(resultats)} veille(s) trouvée(s)")

for i, df in enumerate(resultats, start=1):
    print(f"\nVeille {i}")
    print(df.shape)
# %%
