#%%
import os

from B1.pipeline_veilles import pipeline_veilles_amendements_jour
import json
import requests

DOC_ID = "3XJJmJ8TeyMcRWHEUNj4if"
TABLE_ID = "Test_pipeline"
API_KEY = os.environ["GRIST_API_KEY"]
#%%
veille_1, veille_2 = pipeline_veilles_amendements_jour(
    jour="2026-07-01",
    doc_id=DOC_ID,
    table_id=TABLE_ID,
)


#%%
TABLE_ID = "Test_api_export"

df = veille_1

BASE_URL = "https://docs.getgrist.com/api"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

# ------------------------------------------------------------------
# 1. Création de la table
# ------------------------------------------------------------------

payload = {
    "tables": [
        {
            "id": TABLE_ID,
            "columns": [
                {
                    "id": col,
                    "fields": {
                        "label": col,
                        "type": "Text",
                    },
                }
                for col in df.columns
            ],
        }
    ]
}

r = requests.post(
    f"{BASE_URL}/docs/{DOC_ID}/tables",
    headers=headers,
    json=payload,
)

r.raise_for_status()

print("Table créée :", r.json())

# ------------------------------------------------------------------
# 2. Récupération des vrais ids des colonnes
# ------------------------------------------------------------------

r = requests.get(
    f"{BASE_URL}/docs/{DOC_ID}/tables/{TABLE_ID}/columns",
    headers=headers,
)

r.raise_for_status()

mapping = {
    col["fields"]["label"]: col["id"]
    for col in r.json()["columns"]
}

print(mapping)

# ------------------------------------------------------------------
# 3. Conversion des valeurs
# ------------------------------------------------------------------

def clean(x):
    if x is None:
        return None

    if isinstance(x, (list, dict)):
        return json.dumps(x, ensure_ascii=False)

    return str(x)

# ------------------------------------------------------------------
# 4. Construction des records
# ------------------------------------------------------------------

records = [
    {
        "fields": {
            mapping[col]: clean(val)
            for col, val in row.items()
        }
    }
    for row in df.iter_rows(named=True)
]

# ------------------------------------------------------------------
# 5. Import par batch
# ------------------------------------------------------------------

url = f"{BASE_URL}/docs/{DOC_ID}/tables/{TABLE_ID}/records?noparse=true"

batch_size = 100

for i in range(0, len(records), batch_size):

    batch = records[i:i + batch_size]

    r = requests.post(
        url,
        headers=headers,
        json={"records": batch},
    )

    r.raise_for_status()

    print(
        f"{min(i + batch_size, len(records))}/{len(records)} lignes importées"
    )

print("Import terminé.")